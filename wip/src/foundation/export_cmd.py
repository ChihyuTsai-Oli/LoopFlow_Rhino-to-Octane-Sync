# -*- coding: utf-8 -*-
"""給 Rhino `_-Export` 用的 ASCII 安全路徑（避開中文與括號）。"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable, Optional, Tuple, Union

from foundation.pointer import windows_short_path

PathLike = Union[str, os.PathLike]
ShortPathFn = Callable[[PathLike], Optional[str]]

TEMP_EXPORT_NAME = "r2o_models_pending.usdz"


def rhino_export_target(
    pending: PathLike,
    *,
    short_path_fn: Optional[ShortPathFn] = None,
    temp_dir: Optional[PathLike] = None,
) -> Tuple[str, Optional[Path]]:
    """
    回傳 (指令列路徑, 匯出後要 copy 到的 pending)。

    優先：父目錄 8.3 ＋ ASCII 檔名（與 pending 同一檔）。
    否則：%TEMP%\\r2o_models_pending.usdz，再 copy 到 pending。
    """
    pending_path = Path(pending)
    lookup = short_path_fn if short_path_fn is not None else windows_short_path
    parent = pending_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    short_parent = lookup(parent)
    if short_parent:
        cmd = str(Path(short_parent) / pending_path.name)
        try:
            cmd.encode("ascii")
        except UnicodeEncodeError:
            short_parent = None
        else:
            if "(" not in cmd and ")" not in cmd:
                return cmd, None

    tmp_root = Path(temp_dir) if temp_dir is not None else Path(tempfile.gettempdir())
    tmp_root.mkdir(parents=True, exist_ok=True)
    temp_path = tmp_root / TEMP_EXPORT_NAME
    return str(temp_path), pending_path
