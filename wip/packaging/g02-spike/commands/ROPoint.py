#! python 3
# -*- coding: utf-8 -*-
"""Yak 指令 ROPoint。開發入口仍是 entrypoints/ROPoint.py。"""
from __future__ import annotations

import importlib.util
import os

_CMD = "ROPoint"


def _prepare_src():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "_loopflow_r2o_yak_isolate",
        os.path.join(here, "..", "_isolate.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.isolate_for_yak_command(__file__)


def RunCommand(is_interactive):
    _prepare_src()
    import rhinoscriptsyntax as rs  # type: ignore

    from rhino.commands.point import publish_points_once

    result = publish_points_once()
    msg = "{} [{}] {}".format(_CMD, result.status, result.message)
    print(msg)
    if not result.ok and result.status == "blocked":
        rs.MessageBox(result.message)
