# -*- coding: utf-8 -*-
"""R2O_Objects：發布 models/R2O_Objects_時戳.usdz（材質後處理＋atomic）。"""
from __future__ import annotations

import os
import sys

_CMD = "R2O_Objects"


def _repo_src_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main() -> None:
    src = _repo_src_root()
    if src not in sys.path:
        sys.path.insert(0, src)

    import rhinoscriptsyntax as rs  # type: ignore

    from rhino.commands.objects import publish_objects_once

    result = publish_objects_once(interactive=True)
    msg = "{} [{}] {}".format(_CMD, result.status, result.message)
    print(msg)
    if result.ok:
        rs.MessageBox(
            "Objects export succeeded.\n\n"
            "In Octane: load this USDZ as a standalone component.\n"
            "Do not click Reload mesh or Load new mesh.\n\n"
            "{}".format(result.data or result.message),
            title=_CMD,
        )
    elif result.status in ("blocked", "fail"):
        rs.MessageBox(result.message, title=_CMD)


if __name__ == "__main__":
    main()
