"""Scanned book import — OCR text from PDFs, image folders, and archives.

Handles scanned PDFs where each page is an embedded JPEG image,
as well as folders of scanned page images (JPG, PNG, etc.) and
ZIP/RAR archives containing page images.
Extracts images, runs OCR (tesseract) in any installed language,
and feeds results into the ForumKnowledgeBase.
"""

import os
import re
import tempfile
import zipfile
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger("pdf_import")
_log_initialized = False
def _ensure_log():
    global _log_initialized
    if _log_initialized:
        return
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler("data/logs/pdf_import.log", mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    _log_initialized = True

_ensure_log()


def _has_pymupdf() -> bool:
    try:
        import fitz  # noqa: F401
        return True
    except ImportError:
        return False

def _has_pil() -> bool:
    try:
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False

def _has_tesseract() -> bool:
    try:
        import pytesseract  # noqa: F401
        return True
    except ImportError:
        return False

def _has_rarfile() -> bool:
    try:
        import rarfile  # noqa: F401
        return True
    except ImportError:
        return False

# Module-level aliases (legacy, kept for any external code importing them)
HAS_PYMUPDF = _has_pymupdf()
HAS_PIL = _has_pil()
HAS_TESSERACT = _has_tesseract()
HAS_RARFILE = _has_rarfile()


SUPPORTED_IMAGE_EXTS: Set[str] = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
SUPPORTED_ARCHIVE_EXTS: Set[str] = {".zip", ".rar"}


@dataclass
class ScannedPage:
    """Extracted content from a single scanned page (PDF or image)."""
    page_number: int
    text: str
    source_image: Optional[str] = None


@dataclass
class ScanResult:
    """Result of processing one PDF file or image folder."""
    source: str
    title: str
    total_pages: int
    full_text: str
    page_data: List[ScannedPage] = field(default_factory=list)


def get_available_languages() -> List[str]:
    """Return list of installed Tesseract language packs (system + user tessdata).

    Example: ['ces', 'deu', 'eng', 'fra', 'osd', 'spa', ...]
    """
    if not _has_tesseract():
        return ["eng"]
    import pytesseract
    try:
        langs = set(pytesseract.get_languages())
    except Exception:
        langs = {"eng"}
    # Also scan ~/.tesseract/tessdata/ for user-installed packs
    user_dir = Path.home() / ".tesseract" / "tessdata"
    if user_dir.is_dir():
        for f in user_dir.glob("*.traineddata"):
            langs.add(f.stem)
    return sorted(langs)


def _tesseract_config() -> str:
    """Return Tesseract config string that includes the user tessdata dir if it exists."""
    user_dir = Path.home() / ".tesseract" / "tessdata"
    if user_dir.is_dir():
        return f"--tessdata-dir {user_dir}"
    return ""


def ocr_image(image_path: str, lang: str = "eng") -> str:
    logger.debug("ocr_image start path=%s lang=%s", image_path, lang)
    """Run OCR on a single image file using Tesseract.

    Args:
        image_path: Path to the image file.
        lang: Tesseract language code (e.g. 'eng', 'ces', 'deu+eng').

    Returns:
        Extracted text string.
    """
    import pytesseract
    from PIL import Image
    if not _has_tesseract():
        raise ImportError(
            "pytesseract is required. Run: pip install pytesseract\n"
            "Also install Tesseract itself: apt install tesseract-ocr"
        )
    if not _has_pil():
        raise ImportError("Pillow is required. Run: pip install Pillow")

    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang=lang, config=_tesseract_config())
    return text.strip()


def _image_output_dir(source_name: str) -> Path:
    """Return a persistent directory for extracted images."""
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', source_name)[:64]
    img_dir = Path("data") / "extracted_images" / safe
    img_dir.mkdir(parents=True, exist_ok=True)
    return img_dir


def _copy_with_numbering(source: Path, dest_dir: Path, page_num: int) -> Path:
    """Copy *source* to *dest_dir* as ``<page_num:03d><ext>`` (e.g. 001.jpg)."""
    ext = source.suffix.lower()
    if ext not in SUPPORTED_IMAGE_EXTS:
        ext = ".jpg"
    name = f"{page_num:03d}{ext}"
    dest = dest_dir / name
    import shutil
    shutil.copy2(str(source), str(dest))
    return dest


def ocr_pdf_pages(pdf_path: str, output_dir: Optional[str] = None,
                  lang: str = "eng",
                  progress_callback=None,
                  page_callback=None) -> ScanResult:
    """Extract text + images from a scanned PDF.

    Images are saved to ``data/extracted_images/<title>/`` for
    later access by the LLM.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Where to save extracted images (default: persistent dir).
        lang: Tesseract language code.
        progress_callback: Callable(status_message).
        page_callback: Callable(image_path, page_num, ocr_text) for live preview.

    Returns:
        ScanResult with full text and per-page data.
    """
    logger.info("ocr_pdf_pages start pdf=%s lang=%s", pdf_path, lang)
    import fitz
    import pytesseract
    from PIL import Image
    if not _has_pymupdf():
        raise ImportError("PyMuPDF (fitz) is required. Run: pip install PyMuPDF")

    pdf_name = Path(pdf_path).stem
    if output_dir is None:
        output_dir = str(_image_output_dir(pdf_name))

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    logger.info("PDF has %d pages", total_pages)
    all_text_parts = []
    page_data_list = []
    all_image_paths: List[str] = []

    try:
        for page_num in range(total_pages):
            page = doc[page_num]
            if progress_callback:
                progress_callback(f"  Page {page_num + 1}/{total_pages}...")

            native_text = page.get_text().strip()
            images = page.get_images(full=True)
            ocr_text_parts = []
            page_image_paths = []

            for img_idx, img in enumerate(images):
                xref = img[0]
                base = doc.extract_image(xref)
                ext = base["ext"]
                suffix = chr(97 + img_idx) if img_idx > 0 else ""
                img_filename = f"{page_num + 1:03d}{suffix}.{ext}"
                img_path = Path(output_dir) / img_filename
                img_path.parent.mkdir(parents=True, exist_ok=True)
                with open(img_path, "wb") as f:
                    f.write(base["image"])
                page_image_paths.append(str(img_path))
                all_image_paths.append(str(img_path))

                if _has_tesseract():
                    try:
                        text = pytesseract.image_to_string(
                            Image.open(img_path), lang=lang,
                            config=_tesseract_config()
                        )
                        if text.strip():
                            ocr_text_parts.append(text.strip())
                        else:
                            logger.debug("OCR empty for page %d img %s", page_num + 1, img_path)
                    except Exception as e:
                        logger.error("OCR error page %d img %s: %s", page_num + 1, img_path, e)
                        if progress_callback:
                            progress_callback(f"    OCR error: {e}")

            combined_text = native_text
            if ocr_text_parts:
                if combined_text:
                    combined_text += "\n\n" + "\n\n".join(ocr_text_parts)
                else:
                    combined_text = "\n\n".join(ocr_text_parts)

            first_image = page_image_paths[0] if page_image_paths else None
            if page_callback:
                page_callback(first_image, page_num + 1, combined_text)
            logger.debug("page %d done images=%d ocr_len=%d", page_num + 1, len(page_image_paths), len(combined_text))

            # Append image references to the text for LLM context
            if page_image_paths:
                combined_text += "\n\n[Images on this page:]"
                for ip in page_image_paths:
                    combined_text += f"\n  📷 {ip}"

            page_data_list.append(ScannedPage(
                page_number=page_num + 1,
                text=combined_text,
                source_image=page_image_paths[0] if page_image_paths else None,
            ))
            all_text_parts.append(f"--- Page {page_num + 1} ---\n{combined_text}")

    finally:
        doc.close()

    return ScanResult(
        source=pdf_path,
        title=pdf_name,
        total_pages=total_pages,
        full_text="\n\n".join(all_text_parts),
        page_data=page_data_list,
    )


def ocr_image_folder(folder_path: str, lang: str = "eng",
                     progress_callback=None,
                     page_callback=None) -> ScanResult:
    """OCR all supported images in a folder, sorted by filename.

    Images are copied to ``data/extracted_images/<folder_name>/``
    with sequential numbering (001.jpg, 002.jpg, ...).

    Returns:
        ScanResult with full text and per-image data.
    """
    logger.info("ocr_image_folder start folder=%s lang=%s", folder_path, lang)
    import pytesseract
    from PIL import Image
    if not _has_tesseract():
        raise ImportError(
            "pytesseract is required. Run: pip install pytesseract\n"
            "Also install Tesseract itself: apt install tesseract-ocr"
        )
    if not _has_pil():
        raise ImportError("Pillow is required. Run: pip install Pillow")

    folder = Path(folder_path)
    title = folder.name

    image_files = sorted(
        p for p in folder.iterdir()
        if p.suffix.lower() in SUPPORTED_IMAGE_EXTS
    )
    total_pages = len(image_files)
    logger.info("Found %d image files in %s", total_pages, title)

    # Copy to persistent dir with sequential numbering
    persistent_dir = _image_output_dir(title)
    all_text_parts = []
    page_data_list = []

    for idx, src_path in enumerate(image_files):
        page_num = idx + 1
        if progress_callback:
            progress_callback(f"  Page {page_num}/{total_pages} — {src_path.name}...")

        # Copy with numbered name
        saved_path = _copy_with_numbering(src_path, persistent_dir, page_num)

        try:
            text = pytesseract.image_to_string(
                Image.open(saved_path), lang=lang,
                config=_tesseract_config()
            )
            text = text.strip()
        except Exception as e:
            if progress_callback:
                progress_callback(f"    OCR error on {src_path.name}: {e}")
            logger.warning("OCR failed for %s: %s", saved_path, e)
            text = ""

        text_with_img = text
        if text_with_img:
            text_with_img += f"\n\n[Image: {saved_path}]"
        else:
            text_with_img = f"[Image: {saved_path}]"

        page_data_list.append(ScannedPage(
            page_number=page_num,
            text=text_with_img,
            source_image=str(saved_path),
        ))
        all_text_parts.append(f"--- Page {page_num} ({saved_path.name}) ---\n{text_with_img}")

        if page_callback:
            page_callback(str(saved_path), page_num, text_with_img)

    return ScanResult(
        source=folder_path,
        title=title,
        total_pages=total_pages,
        full_text="\n\n".join(all_text_parts),
        page_data=page_data_list,
    )


def extract_archive(archive_path: str, output_dir: Optional[str] = None) -> str:
    """Extract all files from a ZIP or RAR archive.

    Args:
        archive_path: Path to the archive file (.zip or .rar).
        output_dir: Target directory (default: temp dir named after archive).

    Returns:
        Path to the extraction directory.
    """
    logger.info("extract_archive path=%s", archive_path)
    archive_path = Path(archive_path)
    ext = archive_path.suffix.lower()

    if output_dir is None:
        output_dir = str(Path(tempfile.mkdtemp(prefix=f"{archive_path.stem}_")))
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if ext == ".zip":
        with zipfile.ZipFile(str(archive_path), "r") as zf:
            zf.extractall(str(out))
    elif ext == ".rar":
        if not _has_rarfile():
            raise ImportError(
                "rarfile is required for RAR support. Run: pip install rarfile\n"
                "Also install unrar: apt install unrar"
            )
        with rarfile.RarFile(str(archive_path), "r") as rf:
            rf.extractall(str(out))
    else:
        raise ValueError(f"Unsupported archive format: {ext}")

    return str(out)


def ocr_archive_pages(archive_path: str, lang: str = "eng",
                      progress_callback=None,
                      page_callback=None) -> ScanResult:
    """Extract a ZIP/RAR archive and OCR all images inside.

    Images are numbered 001, 002, ... and saved to
    ``data/extracted_images/<archive_name>/`` for persistent access.

    Returns:
        ScanResult with full text and per-image data.
    """
    archive = Path(archive_path)
    if progress_callback:
        progress_callback(f"Extracting {archive.name}...")

    extract_dir = Path(extract_archive(str(archive)))

    if progress_callback:
        progress_callback(f"OCR-ing images from {archive.name}...")

    # ocr_image_folder copies images to persistent dir with sequential numbering
    return ocr_image_folder(str(extract_dir), lang=lang,
                            progress_callback=progress_callback,
                            page_callback=page_callback)


def import_archive_to_kb(archive_path: str, kb, source_name: str = "",
                         lang: str = "eng",
                         progress_callback=None,
                         page_callback=None) -> int:
    """Extract a ZIP/RAR archive and import all image text to knowledge base.

    Returns:
        Number of pages added.
    """
    logger.info("import_archive_to_kb archive=%s source=%s", archive_path, source_name)
    result = ocr_archive_pages(archive_path, lang=lang,
                               progress_callback=progress_callback,
                               page_callback=page_callback)
    return import_scan_to_kb(result, kb, source_name, progress_callback)


def import_scan_to_kb(result: ScanResult, kb,
                      source_name: str = "",
                      progress_callback=None) -> int:
    """Add a ScanResult into a ForumKnowledgeBase.

    Args:
        result: ScanResult from ocr_pdf_pages or ocr_image_folder.
        kb: ForumKnowledgeBase instance.
        source_name: Label for the source (defaults to title).
        progress_callback: Callable for status messages.

    Returns:
        Number of knowledge entries added.
    """
    from knowledge.base import KnowledgeEntry

    if not source_name:
        source_name = result.title

    added = 0
    logger.info("import_scan_to_kb source=%s total_pages=%d", source_name, result.total_pages)
    for page in result.page_data:
        if not page.text.strip():
            continue
        images = []
        if page.source_image:
            images = [page.source_image]
        entry = KnowledgeEntry(
            source=source_name,
            title=f"{result.title} — Page {page.page_number}",
            content=page.text[:6000],
            category="general",
            image_paths=images,
        )
        kb.entries.append(entry)
        added += 1

    kb._built = True
    return added


def import_pdf_to_kb(pdf_path: str, kb, source_name: str = "",
                     lang: str = "eng",
                     progress_callback=None,
                     page_callback=None) -> int:
    """Process a scanned PDF and add its text to the knowledge base.

    Returns:
        Number of pages added.
    """
    logger.info("import_pdf_to_kb pdf=%s source=%s", pdf_path, source_name)
    result = ocr_pdf_pages(pdf_path, lang=lang, progress_callback=progress_callback,
                           page_callback=page_callback)
    return import_scan_to_kb(result, kb, source_name, progress_callback)


def import_image_folder_to_kb(folder_path: str, kb, source_name: str = "",
                              lang: str = "eng",
                              progress_callback=None,
                              page_callback=None) -> int:
    """OCR all images in a folder and add their text to the knowledge base.

    Returns:
        Number of pages added.
    """
    logger.info("import_image_folder_to_kb folder=%s source=%s", folder_path, source_name)
    result = ocr_image_folder(folder_path, lang=lang, progress_callback=progress_callback,
                              page_callback=page_callback)
    return import_scan_to_kb(result, kb, source_name, progress_callback)


def bulk_import_pdfs(pdf_paths: List[str], kb,
                     source_prefix: str = "Scanned Book",
                     lang: str = "eng",
                     progress_callback=None) -> int:
    """Import multiple PDFs into the knowledge base.
    """
    logger.info("bulk_import_pdfs count=%d prefix=%s", len(pdf_paths), source_prefix)
    total = 0
    for i, path in enumerate(pdf_paths):
        if progress_callback:
            progress_callback(f"[{i+1}/{len(pdf_paths)}] Processing {Path(path).name}...")
        added = import_pdf_to_kb(path, kb, f"{source_prefix}: {Path(path).stem}",
                                  lang=lang, progress_callback=progress_callback)
        total += added
        if progress_callback:
            progress_callback(f"  → {added} pages added")
    return total


def check_dependencies(target_langs: Optional[List[str]] = None) -> Tuple[bool, str]:
    """Check all PDF/OCR/archive dependencies (re-checks on every call).

    Args:
        target_langs: Optional list of Tesseract language codes to verify are installed.

    Returns:
        (all_ok, message) tuple.
    """
    logger.debug("check_dependencies")
    required_missing = []
    optional_missing = []
    if not _has_pymupdf():
        required_missing.append("PyMuPDF (pip install PyMuPDF)")
    if not _has_pil():
        required_missing.append("Pillow (pip install Pillow)")
    if not _has_tesseract():
        required_missing.append("pytesseract (pip install pytesseract)")
    if _has_tesseract():
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
        except Exception:
            required_missing.append("Tesseract OCR engine (apt install tesseract-ocr)")
        else:
            # Check target language packs
            if target_langs:
                installed = set(get_available_languages())
                for lang in target_langs:
                    # Handle combined lang codes like "ces+eng"
                    parts = lang.split("+")
                    missing_parts = [p for p in parts if p not in installed]
                    if missing_parts:
                        for mp in missing_parts:
                            optional_missing.append(
                                f"Tesseract language '{mp}' — "
                                f"download to ~/.tesseract/tessdata/ or "
                                f"apt install tesseract-ocr-{mp}"
                            )
    if not _has_rarfile():
        optional_missing.append("rarfile (pip install rarfile) — only needed for .rar archives")

    parts = []
    if required_missing:
        parts.append("Missing:\n  " + "\n  ".join(required_missing))
    if optional_missing:
        parts.append("Optional:\n  " + "\n  ".join(optional_missing))
    if not required_missing:
        msg = ("; ".join(parts) + "\n\nDependencies OK — ready to import.") if parts else "All PDF/OCR dependencies available"
        return True, msg
    return False, "\n".join(parts) + "\n\nInstall missing packages and restart."
