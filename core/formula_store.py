"""Persistent formula store with git-like version history.

Storage layout (root defaults to ``data/formulas/``)::

    library/<slug>.yaml            # current working formula + _meta
    history/<slug>/v001_<ts>.yaml  # full snapshot per version
    snapshots/<slug>/vNNN_<ts>_<kind>.png  # optional images per version
    formula_log.json               # append-only audit trail

Formulas are opaque dicts (preset_recipes.yaml format) so the store works for
lacquer, plating and pressing formulas alike. All operations are logged.
"""

import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DEFAULT_ROOT = os.path.join(DATA_DIR, "formulas")

_COMPONENT_KEY = "components"
_COMPONENT_ID = "id"


@dataclass
class FormulaRef:
    id: str
    name: str
    version: int
    updated_ts: str
    favorite: bool = False
    tags: List[str] = field(default_factory=list)
    description: str = ""
    image_count: int = 0


@dataclass
class VersionRef:
    number: int
    timestamp: str
    reason: str
    images: List[str] = field(default_factory=list)
    diff: Dict[str, Any] = field(default_factory=dict)


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "untitled"


def _now_compact() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _now_human() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _read_yaml(path: str) -> Any:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _write_yaml(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)


def _version_number(path: str) -> int:
    m = re.search(r"v(\d+)_", os.path.basename(path))
    return int(m.group(1)) if m else 0


def _components_of(data: Dict) -> List[Dict]:
    return list(data.get(_COMPONENT_KEY, []) or [])


def _diff_components(from_comp: List[Dict], to_comp: List[Dict]) -> Dict[str, Any]:
    old = {c.get(_COMPONENT_ID): c for c in from_comp}
    new = {c.get(_COMPONENT_ID): c for c in to_comp}
    added = [c for cid, c in new.items() if cid not in old]
    removed = [c for cid, c in old.items() if cid not in new]
    changed = []
    for cid, c in new.items():
        if cid in old:
            old_conc = old[cid].get("concentration_pct")
            new_conc = c.get("concentration_pct")
            if old_conc != new_conc:
                changed.append({
                    "id": cid,
                    "name": c.get("name", cid),
                    "from": old_conc,
                    "to": new_conc,
                })
    summary = []
    if added:
        summary.append(f"+{len(added)} {_COMPONENT_KEY}")
    if removed:
        summary.append(f"-{len(removed)} {_COMPONENT_KEY}")
    if changed:
        summary.append(f"~{len(changed)} concentrations")
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "summary": ", ".join(summary) or "no component changes",
    }


class FormulaStore:
    def __init__(self, root: Optional[str] = None):
        self.root = os.path.abspath(root or DEFAULT_ROOT)
        self.library_dir = os.path.join(self.root, "library")
        self.history_dir = os.path.join(self.root, "history")
        self.snapshots_dir = os.path.join(self.root, "snapshots")
        self.log_path = os.path.join(self.root, "formula_log.json")
        for d in (self.library_dir, self.history_dir, self.snapshots_dir):
            os.makedirs(d, exist_ok=True)

    def _library_path(self, formula_id: str) -> str:
        return os.path.join(self.library_dir, f"{formula_id}.yaml")

    def _history_dir(self, formula_id: str) -> str:
        return os.path.join(self.history_dir, formula_id)

    def _snapshots_dir(self, formula_id: str) -> str:
        return os.path.join(self.snapshots_dir, formula_id)

    def _log(self, formula_id: str, action: str, version: Optional[int] = None,
             reason: str = "", detail: str = "") -> None:
        entry = {
            "ts": _now_human(),
            "formula_id": formula_id,
            "action": action,
            "version": version,
            "reason": reason,
            "detail": detail,
        }
        entries = self.get_log()
        entries.append(entry)
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def get_log(self, limit: Optional[int] = None) -> List[Dict]:
        if not os.path.exists(self.log_path):
            return []
        try:
            with open(self.log_path, encoding="utf-8") as f:
                entries = json.load(f)
            if not isinstance(entries, list):
                return []
            return entries[-limit:] if limit else entries
        except Exception:
            return []

    def formula_exists(self, formula_id: str) -> bool:
        return os.path.exists(self._library_path(formula_id))

    def create_formula(self, name: str, data: Dict, description: str = "",
                       tags: Optional[List[str]] = None) -> FormulaRef:
        if not name or not name.strip():
            raise ValueError("Formula name must not be empty")
        if not isinstance(data, dict):
            raise ValueError("Formula data must be a dict")
        formula_id = _slug(name)
        if self.formula_exists(formula_id):
            raise ValueError(f"Formula '{name}' already exists")
        data = dict(data)
        data["name"] = name.strip()
        meta = {
            "version": 0,
            "created": _now_human(),
            "updated": _now_human(),
            "favorite": False,
            "tags": tags or [],
            "description": description,
        }
        _write_yaml(self._library_path(formula_id), {"_meta": meta, **data})
        ref = self.commit_version(formula_id, "Initial version")
        self._log(formula_id, "create", version=1, detail=name)
        return FormulaRef(
            id=formula_id, name=data["name"], version=ref.number,
            updated_ts=meta["updated"], favorite=False, tags=tags or [],
            description=description,
        )

    def list_formulas(self) -> List[FormulaRef]:
        refs = []
        if not os.path.isdir(self.library_dir):
            return refs
        for fn in sorted(os.listdir(self.library_dir)):
            if not fn.endswith(".yaml"):
                continue
            formula_id = fn[: -len(".yaml")]
            meta, data = self._read_library(formula_id)
            if meta is None:
                continue
            snap_dir = self._snapshots_dir(formula_id)
            image_count = 0
            if os.path.isdir(snap_dir):
                image_count = sum(
                    1 for f in os.listdir(snap_dir) if f.endswith(".png")
                )
            refs.append(FormulaRef(
                id=formula_id,
                name=data.get("name", formula_id),
                version=meta.get("version", 0),
                updated_ts=meta.get("updated", ""),
                favorite=bool(meta.get("favorite")),
                tags=list(meta.get("tags", [])),
                description=meta.get("description", ""),
                image_count=image_count,
            ))
        return refs

    def _read_library(self, formula_id: str):
        raw = _read_yaml(self._library_path(formula_id))
        if not isinstance(raw, dict):
            return None, None
        meta = raw.get("_meta", {})
        data = {k: v for k, v in raw.items() if k != "_meta"}
        return meta, data

    def get_formula(self, formula_id: str) -> Optional[Dict]:
        if not self.formula_exists(formula_id):
            return None
        return self._read_library(formula_id)[1]

    def get_formula_meta(self, formula_id: str) -> Optional[Dict]:
        if not self.formula_exists(formula_id):
            return None
        return self._read_library(formula_id)[0]

    def save_formula(self, formula_id: str, data: Dict,
                     change_reason: str = "") -> FormulaRef:
        if not self.formula_exists(formula_id):
            raise ValueError(f"Formula '{formula_id}' does not exist")
        meta, _ = self._read_library(formula_id)
        meta["updated"] = _now_human()
        data = dict(data)
        _write_yaml(self._library_path(formula_id), {"_meta": meta, **data})
        self._log(formula_id, "save", version=meta.get("version"))
        ref = FormulaRef(
            id=formula_id, name=data.get("name", formula_id),
            version=meta.get("version", 0),
            updated_ts=meta["updated"], favorite=bool(meta.get("favorite")),
            tags=list(meta.get("tags", [])),
            description=meta.get("description", ""),
        )
        if change_reason:
            ref = self.commit_version(formula_id, change_reason, data=data)
        return ref

    def commit_version(self, formula_id: str, reason: str,
                       data: Optional[Dict] = None,
                       images: Optional[List[str]] = None) -> VersionRef:
        if not self.formula_exists(formula_id):
            raise ValueError(f"Formula '{formula_id}' does not exist")
        meta, current = self._read_library(formula_id)
        payload = dict(data) if data is not None else dict(current)
        history = self.list_versions(formula_id)
        number = (history[-1].number if history else 0) + 1
        ts = _now_compact()
        meta["version"] = number
        meta["updated"] = _now_human()
        vmeta = {
            "version": number,
            "updated": _now_human(),
            "reason": reason,
        }
        _write_yaml(
            os.path.join(self._history_dir(formula_id), f"v{number:03d}_{ts}.yaml"),
            {"_meta": vmeta, **payload},
        )
        _write_yaml(self._library_path(formula_id), {"_meta": meta, **payload})
        images = list(images or [])
        for img in images:
            if os.path.exists(img):
                self.save_snapshot_image(formula_id, number, img)
        ref = VersionRef(number=number, timestamp=_now_human(), reason=reason,
                         images=self.get_snapshot_images(formula_id, number))
        if len(history) > 1:
            ref.diff = self.diff_versions(formula_id, number - 1, number)
        self._log(formula_id, "commit", version=number, reason=reason)
        return ref

    def list_versions(self, formula_id: str) -> List[VersionRef]:
        hdir = self._history_dir(formula_id)
        if not os.path.isdir(hdir):
            return []
        versions = []
        for fn in sorted(os.listdir(hdir)):
            if not fn.endswith(".yaml"):
                continue
            path = os.path.join(hdir, fn)
            number = _version_number(path)
            raw = _read_yaml(path) or {}
            vmeta = raw.get("_meta", {})
            versions.append(VersionRef(
                number=number,
                timestamp=vmeta.get("updated", _now_human()),
                reason=vmeta.get("reason", ""),
                images=self.get_snapshot_images(formula_id, number),
                diff={},
            ))
        for i, v in enumerate(versions):
            if i > 0:
                v.diff = self.diff_versions(formula_id, versions[i - 1].number, v.number)
        return versions

    def get_version(self, formula_id: str, version: int) -> Optional[Dict]:
        hdir = self._history_dir(formula_id)
        if not os.path.isdir(hdir):
            return None
        for fn in os.listdir(hdir):
            if _version_number(os.path.join(hdir, fn)) == version and fn.endswith(".yaml"):
                raw = _read_yaml(os.path.join(hdir, fn)) or {}
                return {k: v for k, v in raw.items() if k != "_meta"}
        return None

    def restore_version(self, formula_id: str, version: int,
                        reason: str = "") -> VersionRef:
        snapshot = self.get_version(formula_id, version)
        if snapshot is None:
            raise ValueError(f"Version {version} not found for '{formula_id}'")
        self.commit_version(formula_id, "Restore checkpoint")
        meta, _ = self._read_library(formula_id)
        meta["updated"] = _now_human()
        snapshot = dict(snapshot)
        snapshot["name"] = self.get_formula(formula_id).get("name", formula_id)
        _write_yaml(self._library_path(formula_id), {"_meta": meta, **snapshot})
        self._log(formula_id, "restore", version=version, reason=reason)
        return self.list_versions(formula_id)[-1]

    def diff_versions(self, formula_id: str, v_from: int, v_to: int) -> Dict[str, Any]:
        from_data = self.get_version(formula_id, v_from)
        to_data = self.get_version(formula_id, v_to)
        if from_data is None or to_data is None:
            return {"added": [], "removed": [], "changed": [], "summary": ""}
        return _diff_components(_components_of(from_data), _components_of(to_data))

    def save_snapshot_image(self, formula_id: str, version: int,
                            image: Any, kind: str = "formula") -> str:
        if isinstance(image, (bytes, bytearray)):
            image_bytes = bytes(image)
            ext = ".png"
        elif isinstance(image, str):
            ext = os.path.splitext(image)[1] or ".png"
            if not os.path.exists(image):
                raise FileNotFoundError(f"Image not found: {image}")
            with open(image, "rb") as f:
                image_bytes = f.read()
        else:
            raise TypeError("image must be bytes or a file path")
        snap_dir = self._snapshots_dir(formula_id)
        os.makedirs(snap_dir, exist_ok=True)
        ts = _now_compact()
        path = os.path.join(snap_dir, f"v{version:03d}_{ts}_{kind}{ext}")
        with open(path, "wb") as f:
            f.write(image_bytes)
        self._log(formula_id, "snapshot", version=version, detail=os.path.basename(path))
        return path

    def get_snapshot_images(self, formula_id: str, version: int) -> List[str]:
        snap_dir = self._snapshots_dir(formula_id)
        if not os.path.isdir(snap_dir):
            return []
        return sorted(
            os.path.join(snap_dir, f)
            for f in os.listdir(snap_dir)
            if f.startswith(f"v{version:03d}_") and f.endswith(".png")
        )

    def delete_snapshot_image(self, formula_id: str, version: int,
                              filename: str) -> None:
        snap_dir = self._snapshots_dir(formula_id)
        path = os.path.join(snap_dir, filename)
        if os.path.exists(path):
            os.remove(path)
            self._log(formula_id, "snapshot_delete", version=version,
                      detail=filename)

    def get_thumbnail(self, formula_id: str) -> Optional[str]:
        versions = self.list_versions(formula_id)
        for v in reversed(versions):
            if v.images:
                return v.images[0]
        return None

    def set_favorite(self, formula_id: str, favorite: bool) -> None:
        meta, _ = self._read_library(formula_id)
        meta["favorite"] = bool(favorite)
        _write_yaml(self._library_path(formula_id), {"_meta": meta, **self.get_formula(formula_id)})
        self._log(formula_id, "favorite", detail=str(bool(favorite)))

    def update_meta(self, formula_id: str, **fields) -> None:
        meta, data = self._read_library(formula_id)
        for key, value in fields.items():
            meta[key] = value
        meta["updated"] = _now_human()
        _write_yaml(self._library_path(formula_id), {"_meta": meta, **data})
        self._log(formula_id, "meta", detail=",".join(fields.keys()))

    def rename_formula(self, formula_id: str, new_name: str) -> FormulaRef:
        if not new_name or not new_name.strip():
            raise ValueError("Formula name must not be empty")
        new_id = _slug(new_name)
        if new_id == formula_id:
            return self._ref_of(formula_id)
        if self.formula_exists(new_id):
            raise ValueError(f"Formula '{new_name}' already exists")
        data = self.get_formula(formula_id)
        data["name"] = new_name.strip()
        os.rename(self._library_path(formula_id), self._library_path(new_id))
        if os.path.isdir(self._history_dir(formula_id)):
            os.rename(self._history_dir(formula_id), self._history_dir(new_id))
        if os.path.isdir(self._snapshots_dir(formula_id)):
            os.rename(self._snapshots_dir(formula_id), self._snapshots_dir(new_id))
        self.save_formula(new_id, data)
        self._log(new_id, "rename", detail=f"{formula_id} -> {new_id}")
        return self._ref_of(new_id)

    def _ref_of(self, formula_id: str) -> FormulaRef:
        for ref in self.list_formulas():
            if ref.id == formula_id:
                return ref
        raise ValueError(f"Formula '{formula_id}' does not exist")

    def delete_formula(self, formula_id: str) -> None:
        if not self.formula_exists(formula_id):
            raise ValueError(f"Formula '{formula_id}' does not exist")
        os.remove(self._library_path(formula_id))
        for d in (self._history_dir(formula_id), self._snapshots_dir(formula_id)):
            if os.path.isdir(d):
                shutil.rmtree(d)
        self._log(formula_id, "delete")
