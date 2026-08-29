# -*- coding: utf-8 -*-
"""R2O_Models：發布 models/models.usdz（材質後處理＋atomic；來源還原）。"""
from __future__ import annotations

import os
import sys

_CMD = "R2O_Models"


def _repo_src_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main() -> None:
    src = _repo_src_root()
    if src not in sys.path:
        sys.path.insert(0, src)

    import rhinoscriptsyntax as rs  # type: ignore

    from rhino.commands.models import publish_models_once

    result = publish_models_once(interactive=True)
    msg = "{} [{}] {}".format(_CMD, result.status, result.message)
    print(msg)
    if result.ok:
        rs.MessageBox(
            "Models export succeeded.\n\n"
            "In Octane: do not click Reload mesh or Load new mesh.\n"
            "Close Octane and reopen it. The linked USDZ updates on startup "
            "and materials stay connected.\n\n"
            "{}".format(result.data or result.message),
            title=_CMD,
        )
    elif result.status in ("blocked", "fail"):
        rs.MessageBox(result.message, title=_CMD)


if __name__ == "__main__":
    main()
