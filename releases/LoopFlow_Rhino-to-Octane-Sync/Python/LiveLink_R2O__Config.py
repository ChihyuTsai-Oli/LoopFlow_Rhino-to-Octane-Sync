# -*- coding: utf-8 -*-
"""
============================================================
模組名稱 (Module)  : LiveLink_R2O__Config
版本 (Version)     : v3.0
日期 (Date)        : 2026-04-27
開發者 (Author)    : Cursor + Claude Sonnet 4.6
開發環境 (Env)     : Rhino 8 (CPython 3.9) / Python 3
============================================================
【功能說明】
LiveLink R2O 系列腳本的共用設定模組。
統一管理 R2O_Path.txt 的讀取、寫入與預設值，
確保所有腳本使用一致的設定邏輯。

【放置位置】
%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Python\LiveLink_R2O__Config.py

【使用方式】
各腳本開頭加入：
    import os, sys
    _HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _HERE)
    from LiveLink_R2O__Config import load_r2o_config

【變數連動注意事項】
- 設定檔：%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt
- R2O 除錯日誌：%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\cursor_R2O_debug_log.txt
============================================================
"""
import os
import re
import tempfile
import traceback
from datetime import datetime

# ── 全域路徑推算（依安裝位置自動推算，不依賴硬編碼） ──────────────────
_PYTHON_DIR    = os.path.dirname(os.path.abspath(__file__))
INSTALL_DIR    = os.path.dirname(_PYTHON_DIR)
DATA_DIR       = os.path.join(INSTALL_DIR, "Data")
CONFIG_DIR     = DATA_DIR
CONFIG_FILE    = os.path.join(DATA_DIR, "R2O_Path.txt")
DEBUG_LOG_FILE = os.path.join(DATA_DIR, "cursor_R2O_debug_log.txt")

# 所有腳本共用的完整預設值（單一真理來源）
DEFAULT_CONFIG = {
    "DataPath":       DATA_DIR,
    "ModelDir":       "",           # 空白 = fallback 至 DataPath
    "PointLayer":     "R2O",
    "ModelFile":      "R2O.usdz",
    "CameraFile":     "R2O_Camera_Sync_Data.lua",
    "PointFile":      "R2O_Point_Sync_Data.lua",
    "PointNgName":    "R2O_Point",
    "PointPrefix":    "R2O_Point_",
    "LastModelLayer": "",
}

# 寫入設定檔時的欄位順序
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
    統一例外落地：
    - Rhino 命令列簡述錯誤
    - 寫入除錯日誌（含時間與 traceback）
    """
    summary = "[{}] 發生錯誤: {}".format(script_name, repr(exc))
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
    原子寫檔：先寫入同資料夾 tmp，再用 os.replace 取代。
    目的：避免 Octane Lua 端讀到半寫入的同步檔。
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
    將 Rhino 圖層末段名稱正規化為可穩定用於 Octane 節點名稱的字串。
    - 僅保留 A-Z a-z 0-9 _ -
    - 其餘字元轉為底線，並壓縮連續底線
    - 去除前後底線/連字號
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
    讀取全域設定檔 R2O_Path.txt。
    - 若檔案不存在：自動建立並寫入所有預設欄位。
    - 若檔案存在但缺少欄位：自動補齊缺少的欄位並回寫。
    - 確保 DataPath 資料夾存在。
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
    """依固定順序寫入設定檔，保留使用者已修改的值。"""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        for key in _FIELD_ORDER:
            f.write("{}: {}\n".format(key, config.get(key, DEFAULT_CONFIG.get(key, ""))))
