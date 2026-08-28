# -*- coding: utf-8 -*-
"""相機自動同步閘：姿態略過＋約 0.2s 節流＋trailing（純邏輯）。"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from foundation.camera_payload import poses_equivalent

Pose = Optional[Tuple[float, ...]]
MIN_INTERVAL_SEC = 0.2


class CameraThrottleGate:
    """View.Modified：未變略過；間隔不足則記 pending，安靜後補寫。"""

    def __init__(self, min_interval: float = MIN_INTERVAL_SEC) -> None:
        self.min_interval = float(min_interval)
        self.last_pose: Pose = None
        self.last_time: float = 0.0
        self.pending_pose: Pose = None
        self.pending_payload: Optional[Dict[str, Any]] = None

    def on_event(self, pose: Pose, payload: Dict[str, Any], now: float) -> str:
        """回傳 skip／write／defer。"""
        if poses_equivalent(pose, self.last_pose):
            self.pending_pose = None
            self.pending_payload = None
            return "skip"
        if (now - self.last_time) >= self.min_interval:
            return "write"
        self.pending_pose = pose
        self.pending_payload = payload
        return "defer"

    def trailing_due(self, now: float) -> bool:
        return self.pending_payload is not None and (now - self.last_time) >= self.min_interval

    def mark_written(self, pose: Pose, now: float) -> None:
        self.last_pose = pose
        self.last_time = now
        self.pending_pose = None
        self.pending_payload = None
