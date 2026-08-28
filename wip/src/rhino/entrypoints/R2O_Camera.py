# -*- coding: utf-8 -*-
"""R2O_Camera：開／關自動同步 toggle（再按一次停止）。"""
from __future__ import annotations

import os
import sys

_CMD = "R2O_Camera"


def _repo_src_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main() -> None:
    src = _repo_src_root()
    if src not in sys.path:
        sys.path.insert(0, src)

    import rhinoscriptsyntax as rs  # type: ignore

    from rhino.commands.camera import camera_toggle_auto

    result = camera_toggle_auto()

    msg = "{} [{}] {}".format(_CMD, result.status, result.message)
    print(msg)
    if not result.ok and result.status == "blocked":
        rs.MessageBox(result.message)


if __name__ == "__main__":
    main()
