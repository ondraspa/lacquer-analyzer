"""Data import GUI tab - scrape Lathe Trolls, PubChem enrichment, etc."""

import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("data_import_gui")
_log_initialized = False
def _ensure_log():
    global _log_initialized
    if _log_initialized:
        return
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler("data/logs/data_import_gui.log", mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    _log_initialized = True

_ensure_log()
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QGroupBox, QCheckBox, QSpinBox, QProgressBar,
    QMessageBox, QListWidget, QListWidgetItem, QTabWidget,
    QLineEdit, QFormLayout, QFileDialog, QComboBox, QSplitter,
    QPlainTextEdit,
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject, QTimer
from PySide6.QtGui import QFont

from src.data_import import (
    LatheTrollsScraper, PubChemImporter, WikipediaChemicalImporter,
    ForumPost, save_to_custom_ingredients, run_ingest_pipeline
)
from src.llm_integration import LocalLLM, ForumKnowledgeBase
from src.rag_config import RAGSettings
from src.data_logger import ImportLog
from ui.knowledge.settings_dialog import RAGSettingsDialog
from src.whatsapp_import import (
    parse_whatsapp_export, import_whatsapp_to_kb,
    parse_whatsapp_web_text, import_whatsapp_text_to_kb,
    detect_stage, messages_to_knowledge_entries,
)
from src.pdf_import import (
    ocr_pdf_pages, import_pdf_to_kb, import_image_folder_to_kb,
    import_archive_to_kb, bulk_import_pdfs, get_available_languages,
    check_dependencies as check_pdf_deps,
)


class ScrapeJob(QObject):
    """Worker object for scraping — runs in a QThread via moveToThread."""
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, scraper: LatheTrollsScraper, use_seed: bool,
                 keywords: List[str] = None, settings=None):
        super().__init__()
        self.scraper = scraper
        self.use_seed = use_seed
        self.keywords = keywords or []
        self.settings = settings
        self._abort = False

    @Slot()
    def run(self):
        try:
            if self.use_seed:
                self.progress.emit("Scraping Lathe Trolls seed threads (8 threads)...")
                posts = []
                for i, thread in enumerate(self.scraper.SEED_THREADS):
                    if self._abort:
                        return
                    self.progress.emit(f"  [{i+1}/{len(self.scraper.SEED_THREADS)}] Fetching: {thread['title'][:50]}...")
                    result = self.scraper._scrape_thread(thread["url"], thread["category"])
                    if result:
                        posts.append(result)
                    import time
                    time.sleep(0.5)
                if not posts:
                    self.progress.emit("  Site unreachable — using built-in fallback knowledge")
                    posts = list(type(self.scraper).__dict__.get('FALLBACK_POSTS', [])) or \
                            __import__('src.data_import', fromlist=['FALLBACK_POSTS']).FALLBACK_POSTS
            else:
                self.progress.emit(f"Searching for: {', '.join(self.keywords)}")
                posts = self.scraper.search_keywords(self.keywords)

            if self._abort:
                return

            self.progress.emit(f"Found {len(posts)} posts")
            self.progress.emit("Extracting ingredient data...")
            ingredients = self.scraper.extract_ingredients_from_posts(posts)

            if self._abort:
                return
            self.progress.emit(f"Found {len(ingredients)} unique ingredients")
            self.finished.emit(posts)

        except Exception as e:
            self.error.emit(str(e))


class EnrichJob(QObject):
    """Worker object for PubChem enrichment — runs in a QThread via moveToThread."""
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, config_dir: str):
        super().__init__()
        self.config_dir = config_dir
        self._abort = False

    @Slot()
    def run(self):
        try:
            from src.ingredient_loader import IngredientLoader
            self.progress.emit("Loading ingredient database...")
            loader = IngredientLoader(self.config_dir)
            ingredients = loader.load_all()
            if self._abort:
                return
            self.progress.emit(f"Loaded {len(ingredients)} ingredients")
            self.progress.emit("Looking up PubChem for each ingredient...")

            importer = PubChemImporter()
            preview = []
            found = 0
            skipped = 0
            for i, ing in enumerate(ingredients):
                if self._abort:
                    return
                self.progress.emit(f"  [{i+1}/{len(ingredients)}] {ing.name}...")
                enriched = importer.enrich_ingredient(ing)
                chem_data = {k: v for k, v in enriched.properties.items() if k.startswith("pubchem_")}
                if chem_data:
                    found += 1
                    preview.append(f"{enriched.name}: CAS={chem_data.get('pubchem_cas','?')} "
                                   f"MW={chem_data.get('pubchem_mw','?')}")
                else:
                    skipped += 1

            self.progress.emit(f"Done. Found data for {found}/{len(ingredients)} ingredients "
                               f"({skipped} not in PubChem)")
            self.finished.emit(preview)
        except Exception as e:
            self.error.emit(str(e))


class MirrorJob(QObject):
    """Worker object for forum mirroring — runs via threading.Thread.

    Runs the external ``troll_scraper_stealth.py`` script as a subprocess,
    which uses the Two-Step Playwright architecture (``auth_state.json``)
    to bypass Imperva/Incapsula WAF.  Writes markdown files to
    ``~/lathetrolls_knowledge_base/``, then auto-loads them into
    ``ForumKnowledgeBase``.
    """

    progress_signal = Signal(str)
    finished_signal = Signal(int)
    error_signal = Signal(str)
    done_signal = Signal()

    def __init__(self, on_progress=None, on_finished=None, on_error=None, on_done=None,
                 settings=None, save_images=False, auth_state_path="config/auth_state.json"):
        super().__init__()
        self.on_progress = on_progress
        self.on_finished = on_finished
        self.on_error = on_error
        self.on_done = on_done
        self.settings = settings
        self.save_images = save_images
        self.auth_state_path = auth_state_path
        self._abort = False

        # Connect signals to main-thread-safe forwarding
        self.progress_signal.connect(self._on_progress)
        self.finished_signal.connect(self._on_finished)
        self.error_signal.connect(self._on_error)
        self.done_signal.connect(self._on_done)

    def _on_progress(self, msg):
        if self.on_progress:
            self.on_progress(msg)

    def _on_finished(self, n):
        if self.on_finished:
            self.on_finished(n)

    def _on_error(self, msg):
        if self.on_error:
            self.on_error(msg)

    def _on_done(self):
        if self.on_done:
            self.on_done()

    def run(self):
        import sys as _sys, subprocess, os as _os
        _sys.stderr.write("[MirrorJob] run() entered\n")
        _sys.stderr.flush()

        def _progress(msg):
            _sys.stderr.write(f"[MirrorJob] {msg}\n")
            _sys.stderr.flush()
            self.progress_signal.emit(msg)

        def _done():
            self.done_signal.emit()

        # Locate troll_scraper_stealth.py — sibling of this project or in $HOME
        script_paths = [
            _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "troll_scraper_stealth.py"),
            _os.path.expanduser("~/troll_scraper_stealth.py"),
        ]
        script_path = None
        for p in script_paths:
            if _os.path.exists(p):
                script_path = p
                break

        if not script_path:
            _progress("troll_scraper_stealth.py not found — falling back to built-in Playwright mirror")
            try:
                local_scraper = LatheTrollsScraper(
                    search_max_pages=getattr(self.settings, 'scrape_search_max_pages', 2),
                    forum_max_pages=getattr(self.settings, 'scrape_forum_max_pages', 5),
                    mirror_max_pages=getattr(self.settings, 'scrape_mirror_max_pages', 3),
                    save_images=self.save_images,
                    auth_state_path=self.auth_state_path,
                )
                _progress("Mirroring forum via Playwright (browser will open)...")
                n = local_scraper.mirror_forum_to_markdown(
                    output_dir="~/lathetrolls_knowledge_base",
                    max_threads=0,
                    progress_callback=_progress,
                )
                self.finished_signal.emit(n)
                local_scraper.close()
            except Exception as e:
                self.error_signal.emit(str(e))
            finally:
                _done()
            return

        try:
            _progress(f"Launching troll_scraper_stealth.py as subprocess...")
            _progress("(A Chromium browser will open — let it run, it's fully automatic)")

            # Resolve the project root for OUTPUT_DIR
            project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
            cwd = _os.path.dirname(script_path) or "."

            # Ensure auth_state.json is in the cwd
            if not _os.path.exists(_os.path.join(cwd, "auth_state.json")):
                # Copy from project config if available
                project_auth = _os.path.join(project_root, "config", "auth_state.json")
                if _os.path.exists(project_auth):
                    import shutil
                    shutil.copy2(project_auth, _os.path.join(cwd, "auth_state.json"))
                    _progress("Copied auth_state.json from config/ to script directory")

            # Prefer the scraper_env venv Python (has Playwright), fall back to sys.executable
            venv_python = _os.path.join(project_root, "scraper_env", "bin", "python")
            python_exe = venv_python if _os.path.exists(venv_python) else sys.executable
            _progress(f"Using Python: {python_exe}")
            _progress(f"Script: {script_path}")
            _progress(f"CWD: {cwd}")

            start_id = getattr(self.settings, 'mirror_start_id', 2)
            end_id = getattr(self.settings, 'mirror_end_id', 0)
            cmd = [python_exe, "-u", script_path, "--start", str(start_id)]
            if end_id > 0:
                cmd.extend(["--end", str(end_id)])
            _progress(f"Thread range: {start_id} – {end_id if end_id > 0 else 'auto-discover'}")
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Read output line by line
            seen_output = set()
            for line in proc.stdout:
                line = line.rstrip()
                if line and line not in seen_output:
                    seen_output.add(line)
                    _progress(line)

            proc.wait()
            if self._abort:
                proc.kill()
                return

            # Count markdown files written
            output_dir = _os.path.join(cwd, "lathetrolls_knowledge_base")
            md_files = [f for f in _os.listdir(output_dir)
                        if f.endswith(".md")] if _os.path.isdir(output_dir) else []
            _progress(f"Mirror complete: {len(md_files)} markdown files written")
            self.finished_signal.emit(len(md_files))

        except Exception as e:
            import traceback
            _sys.stderr.write(f"[MirrorJob] ERROR: {e}\n")
            traceback.print_exc(file=_sys.stderr)
            _sys.stderr.flush()
            self.error_signal.emit(str(e))
        finally:
            _done()


class LLMAskJob(QObject):
    """Worker object for LLM question answering — runs in QThread via moveToThread.

    Prevents UI freeze during the synchronous HTTP call to LM Studio,
    and avoids SIGSEGV from accessing deleted Qt objects when user
    closes the window during a long LLM response.
    """
    finished = Signal(str)  # answer text
    error = Signal(str)

    def __init__(self, llm, question: str, context: str = "",
                 max_tokens: int = 1024, temperature: float = 0.3,
                 context_chars: int = 24000,
                 system_prompt: str = ""):
        super().__init__()
        self.llm = llm
        self.question = question
        self.context = context
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.context_chars = context_chars
        self.system_prompt = system_prompt
        self._abort = False

    @Slot()
    def run(self):
        if self._abort:
            return
        try:
            answer = self.llm.ask(
                self.question,
                context=self.context,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                context_chars=self.context_chars,
                system_prompt=self.system_prompt,
            )
            if not self._abort:
                self.finished.emit(answer)
        except Exception as e:
            if not self._abort:
                self.error.emit(str(e))


class PdfImportJob(QObject):
    """Worker for scanned book import — runs in QThread via moveToThread."""
    progress = Signal(str)
    page_progress = Signal(str, int, str)  # image_path, page_num, ocr_text
    finished = Signal(int)  # pages added
    error = Signal(str)

    def __init__(self, items: list, kb, source_prefix: str, lang: str):
        super().__init__()
        self.items = items  # list of (kind, path) tuples
        self.kb = kb
        self.source_prefix = source_prefix
        self.lang = lang
        self._abort = False

    @Slot()
    def run(self):
        total = 0
        for idx, (kind, path) in enumerate(self.items):
            if self._abort:
                return
            label = path if kind == "pdf" else Path(path).name
            self.progress.emit(f"[{idx+1}/{len(self.items)}] {label}...")
            try:
                def _page_cb(img_path, pnum, octext):
                    if not self._abort:
                        self.page_progress.emit(img_path, pnum, octext)
                if kind == "folder":
                    from src.pdf_import import import_image_folder_to_kb
                    added = import_image_folder_to_kb(
                        path, self.kb, self.source_prefix, lang=self.lang,
                        progress_callback=lambda m: self.progress.emit(m),
                        page_callback=_page_cb,
                    )
                elif kind == "archive":
                    from src.pdf_import import import_archive_to_kb
                    added = import_archive_to_kb(
                        path, self.kb, self.source_prefix, lang=self.lang,
                        progress_callback=lambda m: self.progress.emit(m),
                        page_callback=_page_cb,
                    )
                else:
                    from src.pdf_import import import_pdf_to_kb
                    added = import_pdf_to_kb(
                        path, self.kb, self.source_prefix, lang=self.lang,
                        progress_callback=lambda m: self.progress.emit(m),
                        page_callback=_page_cb,
                    )
                total += added
                self.progress.emit(f"  → {added} pages")
            except Exception as e:
                self.error.emit(f"ERROR on {label}: {e}")
        if not self._abort:
            self.finished.emit(total)


class PatentImportJob(QObject):
    """Worker for importing patents from Google Patents."""
    progress = Signal(str)
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, patent_numbers: list, kb, source_prefix: str):
        super().__init__()
        self.patent_numbers = patent_numbers
        self.kb = kb
        self.source_prefix = source_prefix
        self._abort = False

    @Slot()
    def run(self):
        total = 0
        for i, num in enumerate(self.patent_numbers):
            if self._abort:
                return
            label = num.strip().replace(" ", "")
            self.progress.emit(f"[{i+1}/{len(self.patent_numbers)}] {label}...")
            try:
                from src.patent_import import fetch_patent, parse_patent, import_patent_to_kb
                html = fetch_patent(label)
                if html is None:
                    self.progress.emit(f"  ✗ {label}: fetch failed")
                    continue
                data = parse_patent(html)
                if data is None:
                    self.progress.emit(f"  ✗ {label}: parse failed")
                    continue
                n = import_patent_to_kb(data, self.kb, self.source_prefix,
                                        progress_callback=lambda m: self.progress.emit(m))
                total += n
            except Exception as e:
                self.error.emit(f"ERROR on {label}: {e}")
        if not self._abort:
            self.finished.emit(total)


class CacheImportJob(QObject):
    """Worker for importing a cache folder — runs in QThread."""
    progress = Signal(str)
    finished = Signal(list)  # list of ForumPost
    error = Signal(str)

    def __init__(self, scraper, folder_path: str):
        super().__init__()
        self.scraper = scraper
        self.folder_path = folder_path
        self._abort = False

    @Slot()
    def run(self):
        if self._abort:
            return
        try:
            posts = self.scraper.import_cache_folder(
                self.folder_path,
                progress_callback=lambda m: self.progress.emit(m)
            )
            if not self._abort:
                self.finished.emit(posts)
        except Exception as e:
            self.error.emit(str(e))


class BackfillJob(QObject):
    """Worker for backfilling forum images — runs in QThread."""
    progress = Signal(str)
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, scraper):
        super().__init__()
        self.scraper = scraper
        self._abort = False

    @Slot()
    def run(self):
        if self._abort:
            return
        try:
            total = self.scraper.download_missing_images(
                progress_callback=lambda m: self.progress.emit(m)
            )
            if not self._abort:
                self.finished.emit(total)
        except Exception as e:
            self.error.emit(str(e))


class SanitizeJob(QObject):
    """Worker for LLM knowledge sanitization — runs in QThread."""
    progress = Signal(str)
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, llm, entries: list):
        super().__init__()
        self.llm = llm
        self.entries = entries
        self._abort = False

    @Slot()
    def run(self):
        if self._abort:
            return
        try:
            sanitized = self.llm.sanitize_batch(
                self.entries,
                progress_callback=lambda m: self.progress.emit(m)
            )
            if not self._abort:
                self.entries[:] = sanitized
                self.finished.emit(len(sanitized))
        except Exception as e:
            self.error.emit(str(e))
