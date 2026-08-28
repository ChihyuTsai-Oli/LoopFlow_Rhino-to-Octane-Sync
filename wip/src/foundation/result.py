# -*- coding: utf-8 -*-
"""操作結果（純 Python；無 Rhino／Octane 依賴）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Result:
    """指令／發布步驟的統一回傳。"""

    ok: bool
    status: str  # success | fail | cancel | blocked
    message: str
    stage: str = ""
    data: Optional[Any] = None

    @classmethod
    def success(cls, message: str = "", stage: str = "", data: Any = None) -> "Result":
        return cls(ok=True, status="success", message=message, stage=stage, data=data)

    @classmethod
    def fail(cls, message: str, stage: str = "", data: Any = None) -> "Result":
        return cls(ok=False, status="fail", message=message, stage=stage, data=data)

    @classmethod
    def cancel(cls, message: str = "Cancelled", stage: str = "", data: Any = None) -> "Result":
        return cls(ok=False, status="cancel", message=message, stage=stage, data=data)

    @classmethod
    def blocked(cls, message: str, stage: str = "", data: Any = None) -> "Result":
        """無法繼續但非例外失敗（例如未存檔、非透視視埠）。"""
        return cls(ok=False, status="blocked", message=message, stage=stage, data=data)
