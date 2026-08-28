# -*- coding: utf-8 -*-
"""R2O 2.0 foundation：result／path／atomic／log／camera／pointer。"""

from foundation.atomic import (
    atomic_publish_json,
    atomic_publish_text,
    direct_overwrite_json,
)
from foundation.camera_payload import (
    SCHEMA_VERSION,
    build_camera_payload,
    parse_camera_payload,
    validate_camera_payload,
)
from foundation.log import append_log
from foundation.paths import (
    CAMERA_FILE_NAME,
    CONFIG_FILE_NAME,
    CONFIG_PARENT_NAME,
    LOG_FILE_NAME,
    PRODUCT_DIR_NAME,
    camera_path,
    config_path,
    config_root_for_document,
    ensure_config_layout,
    log_path,
    pending_path_for,
    require_saved_document_path,
)
from foundation.pointer import write_current_project_pointer
from foundation.result import Result

__all__ = [
    "Result",
    "SCHEMA_VERSION",
    "build_camera_payload",
    "parse_camera_payload",
    "validate_camera_payload",
    "require_saved_document_path",
    "config_root_for_document",
    "ensure_config_layout",
    "camera_path",
    "config_path",
    "log_path",
    "pending_path_for",
    "atomic_publish_json",
    "atomic_publish_text",
    "direct_overwrite_json",
    "append_log",
    "write_current_project_pointer",
    "CONFIG_PARENT_NAME",
    "PRODUCT_DIR_NAME",
    "CONFIG_FILE_NAME",
    "LOG_FILE_NAME",
    "CAMERA_FILE_NAME",
]
