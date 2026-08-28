# -*- coding: utf-8 -*-
"""XF-ED-04：這台電腦目前專案指標（不放 live／models）。"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Union

from foundation.result import Result

PathLike = Union[str, os.PathLike]

POINTER_SCHEMA_VERSION = 1
POINTER_PRODUCT = "loopflow_R2O"
POINTER_RELATIVE = Path("LoopFlow") / "R2O" / "current_project.json"


def pointer_path() -> Path:
    """`%APPDATA%\\LoopFlow\\R2O\\current_project.json`。"""
    appdata = os.environ.get("APPDATA") or ""
    if not appdata:
        raise OSError("APPDATA is not set")
    return Path(appdata) / POINTER_RELATIVE


def windows_short_path(path: PathLike) -> Optional[str]:
    """Windows 8.3 短路徑（純 ASCII），給 Octane Lua `io.open` 用。"""
    if os.name != "nt":
        return None
    text = str(Path(path))
    try:
        import ctypes
        from ctypes import wintypes

        GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
        GetShortPathNameW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        GetShortPathNameW.restype = wintypes.DWORD
        buf = ctypes.create_unicode_buffer(32768)
        n = GetShortPathNameW(text, buf, 32768)
        if n == 0:
            return None
        short = buf.value
        short.encode("ascii")
        return short
    except (AttributeError, OSError, UnicodeEncodeError):
        return None


def build_pointer_payload(
    *,
    config_root: PathLike,
    document_path: PathLike,
) -> dict:
    payload = {
        "schema_version": POINTER_SCHEMA_VERSION,
        "product": POINTER_PRODUCT,
        "config_root": str(Path(config_root)),
        "document": str(Path(document_path)),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    short = windows_short_path(config_root)
    if short:
        payload["config_root_short"] = short
    return payload


def validate_pointer_payload(data: Any) -> Optional[str]:
    if not isinstance(data, Mapping):
        return "Pointer JSON root must be an object"
    try:
        ver = int(data.get("schema_version"))
    except (TypeError, ValueError):
        return "Missing or invalid schema_version"
    if ver != POINTER_SCHEMA_VERSION:
        return "Unsupported pointer schema_version: {}".format(ver)
    if str(data.get("product") or "") != POINTER_PRODUCT:
        return "Pointer product must be {}".format(POINTER_PRODUCT)
    root = str(data.get("config_root") or "").strip()
    if not root:
        return "Pointer config_root is empty"
    return None


def write_current_project_pointer(
    config_root: PathLike,
    document_path: PathLike,
) -> Result:
    """寫入本機指標；失敗不擋相機發布（呼叫端可忽略）。"""
    stage = "write_pointer"
    try:
        payload = build_pointer_payload(
            config_root=config_root,
            document_path=document_path,
        )
        path = pointer_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_name(path.stem + "_pending" + path.suffix)
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        pending.write_text(text, encoding="utf-8")
        os.replace(str(pending), str(path))
        return Result.success("Pointer updated: {}".format(path), stage=stage, data=str(path))
    except Exception as exc:
        return Result.fail("Failed to write project pointer: {}".format(exc), stage=stage)


def read_current_project_pointer() -> Result:
    """讀本機指標；缺檔或無效則 fail，不猜測。"""
    stage = "read_pointer"
    try:
        path = pointer_path()
    except OSError as exc:
        return Result.fail(str(exc), stage=stage)
    if not path.is_file():
        return Result.fail("Project pointer not found: {}".format(path), stage=stage)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return Result.fail("Project pointer could not be parsed: {}".format(exc), stage=stage)
    err = validate_pointer_payload(data)
    if err:
        return Result.fail(err, stage=stage)
    return Result.success(stage=stage, data=data)
