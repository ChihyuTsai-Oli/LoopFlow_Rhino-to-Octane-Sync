# -*- coding: utf-8 -*-
"""
============================================================
Module Name        : LiveLink_R2O__Config
Version            : v1.0
Date               : 2026-04-28
Author             : Cursor + Claude Sonnet 4.6
Environment        : Rhino 8 (CPython 3.9) / Python 3
============================================================
[Description]
Shared configuration module for the LiveLink R2O script series.
Centralizes reading, writing, and default values for R2O_Path.txt,
ensuring consistent configuration logic across all scripts.

[Install Location]
%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Py\LiveLink_R2O__Config.py

[Usage]
Add the following lines to the top of each script:
    import os, sys
    _HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _HERE)
    from LiveLink_R2O__Config import load_r2o_config

[Variable Notes]
- Config file : %APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt
- Debug log   : %APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\cursor_R2O_debug_log.txt
============================================================
"""
import os
import re
import tempfile
import traceback
from datetime import datetime

# ── Global path resolution (auto-derived from install location, no hard-coding) ──
_PYTHON_DIR    = os.path.dirname(os.path.abspath(__file__))
INSTALL_DIR    = os.path.dirname(_PYTHON_DIR)
DATA_DIR       = os.path.join(INSTALL_DIR, "Data")
CONFIG_DIR     = DATA_DIR
CONFIG_FILE    = os.path.join(DATA_DIR, "R2O_Path.txt")
DEBUG_LOG_FILE = os.path.join(DATA_DIR, "cursor_R2O_debug_log.txt")

# Complete default values shared by all scripts (single source of truth)
DEFAULT_CONFIG = {
    "DataPath":       DATA_DIR,
    "ModelDir":       "",           # Empty = fallback to DataPath
    "PointLayer":     "R2O",
    "ModelFile":      "R2O.usdz",
    "CameraFile":     "R2O_Camera_Sync_Data.lua",
    "PointFile":      "R2O_Point_Sync_Data.lua",
    "PointNgName":    "R2O_Point",
    "PointPrefix":    "R2O_Point_",
    "LastModelLayer": "",
}

# Field order when writing the config file
_FIELD_ORDER = [
    "DataPath",
    "ModelDir",
    "PointLayer",
    "ModelFile",
    "CameraFile",
    "PointFile",
    "PointNgName",
    "PointPrefix",
    "LastModelLayer",
]

def append_debug_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[{}] {}\n".format(timestamp, message)
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def log_exception(script_name, exc, context=None):
    """
    Centralised exception handler:
    - Prints a brief error summary to the Rhino command line
    - Writes details (timestamp + traceback) to the debug log
    """
    summary = "[{}] Error: {}".format(script_name, repr(exc))
    try:
        print(summary)
    except Exception:
        pass

    details = []
    details.append(summary)
    if context:
        try:
            details.append("Context: {}".format(context))
        except Exception:
            pass
    details.append(traceback.format_exc())
    append_debug_log("\n".join(details))


def safe_write_text_atomic(file_path, text, encoding="utf-8"):
    """
    Atomic file write: write to a temp file in the same directory, then replace via os.replace.
    Purpose: prevents Octane Lua from reading a partially-written sync file.
    """
    target_dir = os.path.dirname(file_path)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir)

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=".__tmp__", suffix=".tmp", dir=target_dir or None)
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def normalize_type_name(raw_name, default_name="Default"):
    """
    Normalise a Rhino layer's terminal segment name into a stable string
    suitable for use as an Octane node name.
    - Keeps only A-Z a-z 0-9 _ -
    - Other characters are replaced with underscores; consecutive underscores are collapsed
    - Leading/trailing underscores and hyphens are stripped
    """
    if raw_name is None:
        return default_name

    try:
        name = str(raw_name).strip()
    except Exception:
        return default_name

    if not name:
        return default_name

    name = re.sub(r"[^A-Za-z0-9_-]+", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_-")
    return name or default_name


def load_r2o_config():
    """
    Load the global config file R2O_Path.txt.
    - If missing: auto-create and write all default fields.
    - If present but incomplete: backfill missing fields and rewrite.
    - Ensures the DataPath directory exists.
    """
    config = DEFAULT_CONFIG.copy()

    if not os.path.exists(CONFIG_FILE):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        _write_config(config)
    else:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key in config:
                        config[key] = val

        needs_update = False
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        for key in _FIELD_ORDER:
            if key + ":" not in content:
                needs_update = True
                break

        if needs_update:
            _write_config(config)

    if not os.path.exists(config["DataPath"]):
        os.makedirs(config["DataPath"])

    return config


def _write_config(config):
    """Write the config file in a fixed field order, preserving any user-modified values."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        for key in _FIELD_ORDER:
            f.write("{}: {}\n".format(key, config.get(key, DEFAULT_CONFIG.get(key, ""))))
