# -*- coding: utf-8 -*-
"""給 Rhino `_-Export` 用的 ASCII TEMP 路徑（避開中文與括號）。"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Union

PathLike = Union[str, os.PathLike]


def _ascii_filename(name: str, fallback: str) -> str:
    try:
        name.encode("ascii")
    except UnicodeEncodeError:
        return fallback
    if "(" in name or ")" in name:
        return fallback
    return name


def _stem_from_pending(pending: Path) -> str:
    stem = pending.stem
    if stem.endswith("_pending"):
        stem = stem[: -len("_pending")]
    return stem or "r2o_export"


def rhino_export_target(
    pending: PathLike,
    *,
    export_name: Optional[str] = None,
    attempt: int = 0,
    temp_dir: Optional[PathLike] = None,
) -> Tuple[str, Path]:
    """
    一律寫 `%TEMP%` ASCII 檔，再 copy 到 pending。

    `export_name` 用正式檔名（例如 `R2O.usdz`），讓 zip 內 USDA 一開始就叫 `R2O.usda`。
    `attempt`＞0 時檔名加 `_rN`，避開殘留鎖定。
    """
    pending_path = Path(pending)
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = pending_path.suffix or ".usdz"
    if export_name:
        given = Path(export_name)
        stem = given.stem or _stem_from_pending(pending_path)
        suffix = given.suffix or suffix
    else:
        stem = _stem_from_pending(pending_path)
    stem = _ascii_filename(stem, "r2o_export")
    if attempt:
        fname = "{}_r{}{}".format(stem, attempt, suffix)
    else:
        fname = "{}{}".format(stem, suffix)
    fname = _ascii_filename(fname, "r2o_export{}".format(suffix))
    tmp_root = Path(temp_dir) if temp_dir is not None else Path(tempfile.gettempdir())
    tmp_root.mkdir(parents=True, exist_ok=True)
    return str(tmp_root / fname), pending_path
