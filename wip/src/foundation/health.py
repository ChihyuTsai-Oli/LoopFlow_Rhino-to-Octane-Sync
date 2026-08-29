# -*- coding: utf-8 -*-
"""Open／Health 摘要（純 Python；不依賴 Rhino／Octane）。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Union

from foundation.paths import (
    camera_path,
    latest_objects_path,
    log_path,
    models_path,
    point_path,
)

PathLike = Union[str, Path]


def file_stamp(path: PathLike) -> str:
    """存在則本地時間；否則 missing。"""
    p = Path(path)
    if not p.is_file():
        return "missing"
    try:
        ts = datetime.fromtimestamp(p.stat().st_mtime)
    except OSError:
        return "unreadable"
    return ts.strftime("%Y-%m-%d %H:%M")


def build_health_report(
    *,
    document: str,
    config_root: PathLike,
    work_folder: PathLike,
) -> str:
    root = Path(config_root)
    latest_objects = latest_objects_path(root)
    lines = [
        "R2O Health",
        "",
        "Document: {}".format(document or "(none)"),
        "Config root: {}".format(root),
        "Work folder: {}".format(work_folder),
        "",
        "Camera:  {}  {}".format("live/camera.json", file_stamp(camera_path(root))),
        "Point:   {}  {}".format("live/point.json", file_stamp(point_path(root))),
        "Models:  {}  {}".format("models/R2O.usdz", file_stamp(models_path(root))),
        "Objects: {}  {}".format(
            latest_objects.name if latest_objects else "models/R2O_Objects_YYMMDD_HHMMSS.usdz",
            file_stamp(latest_objects) if latest_objects else "missing",
        ),
        "Log:     {}  {}".format("r2o.log", file_stamp(log_path(root))),
    ]
    return "\n".join(lines)
