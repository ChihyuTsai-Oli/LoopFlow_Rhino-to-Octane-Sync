# -*- coding: utf-8 -*-
"""R2O 專案設定根與交換檔路徑（camera／point／R2O.usdz／Objects 時戳已凍結）。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

from foundation.object_stamp import latest_stamped_path, unique_stamped_path
from foundation.result import Result

PathLike = Union[str, os.PathLike]

CONFIG_PARENT_NAME = "_LoopFlow_Config"
PRODUCT_DIR_NAME = "loopflow_R2O"

LIVE_DIR_NAME = "live"
MODELS_DIR_NAME = "models"

CONFIG_FILE_NAME = "config.json"
LOG_FILE_NAME = "r2o.log"
CAMERA_FILE_NAME = "camera.json"
POINT_FILE_NAME = "point.json"
MODELS_FILE_NAME = "R2O.usdz"
OBJECTS_PREFIX = "R2O_Objects"
OBJECTS_SUFFIX = ".usdz"


def require_saved_document_path(doc_path: Optional[str]) -> Result:
    """未存檔工作檔不得發布設定／交換檔。"""
    if not doc_path or not str(doc_path).strip():
        return Result.blocked("Save the Rhino file first", stage="require_saved")
    path = Path(doc_path)
    if not path.is_file():
        return Result.blocked(
            "Document path is invalid or missing: {}".format(doc_path),
            stage="require_saved",
        )
    return Result.success(data=str(path.resolve()), stage="require_saved")


def config_root_for_document(doc_path: PathLike) -> Path:
    """已存檔 `.3dm` 旁的 `_LoopFlow_Config/loopflow_R2O/`。"""
    doc = Path(doc_path).resolve()
    return doc.parent / CONFIG_PARENT_NAME / PRODUCT_DIR_NAME


def live_dir(root: PathLike) -> Path:
    return Path(root) / LIVE_DIR_NAME


def models_dir(root: PathLike) -> Path:
    return Path(root) / MODELS_DIR_NAME


def camera_path(root: PathLike) -> Path:
    return live_dir(root) / CAMERA_FILE_NAME


def point_path(root: PathLike) -> Path:
    return live_dir(root) / POINT_FILE_NAME


def models_path(root: PathLike) -> Path:
    return models_dir(root) / MODELS_FILE_NAME


def next_objects_path(root: PathLike) -> Path:
    """`models/R2O_Objects_YYMMDD_HHMMSS.usdz`（尚未占用的時戳）。"""
    return unique_stamped_path(models_dir(root), OBJECTS_PREFIX, OBJECTS_SUFFIX)


def latest_objects_path(root: PathLike) -> Optional[Path]:
    return latest_stamped_path(models_dir(root), OBJECTS_PREFIX, OBJECTS_SUFFIX)


def config_path(root: PathLike) -> Path:
    return Path(root) / CONFIG_FILE_NAME


def log_path(root: PathLike) -> Path:
    return Path(root) / LOG_FILE_NAME


def pending_path_for(final_path: PathLike) -> Path:
    """同目錄：`name.ext` → `name_pending.ext`。"""
    final = Path(final_path)
    return final.with_name("{}_pending{}".format(final.stem, final.suffix))


def ensure_config_layout(root: PathLike) -> Path:
    """建立設定根與 live／models 子目錄；回傳 resolve 後的 root。"""
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    live_dir(root_path).mkdir(parents=True, exist_ok=True)
    models_dir(root_path).mkdir(parents=True, exist_ok=True)
    return root_path.resolve()
