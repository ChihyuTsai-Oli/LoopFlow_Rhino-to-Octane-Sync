# -*- coding: utf-8 -*-
"""Scatter USD 檔名：保留中文；只清 Windows 非法字元。不洗成 unnamed_block。"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from foundation.result import Result

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def scatter_file_stem(block_name: str) -> Optional[str]:
    """Block 定義名 → 檔名單（不含 .usd）。空名或不合法則 None。"""
    name = (block_name or "").strip()
    if not name:
        return None
    name = _ILLEGAL.sub("_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip(" ._")
    if not name or name in (".", ".."):
        return None
    return name


def map_block_stems(block_names: Sequence[str]) -> Result:
    """
    回傳 {stem: 原始 Block 名}。

    空名、或兩個不同定義洗成同一檔名 → 整批 fail（寫檔前）。
    """
    stem_to_source: Dict[str, str] = {}
    collisions: List[Tuple[str, str, str]] = []
    empty: List[str] = []
    for raw in block_names:
        stem = scatter_file_stem(raw)
        if not stem:
            empty.append(raw or "(empty)")
            continue
        if stem in stem_to_source and stem_to_source[stem] != raw:
            collisions.append((stem, stem_to_source[stem], raw))
            continue
        stem_to_source[stem] = raw
    if empty:
        return Result.fail(
            "Block name(s) cannot be used as file names: {}".format(", ".join(empty)),
            stage="scatter_names",
        )
    if collisions:
        bits = [
            "'{}' and '{}' both become {}.usd".format(a, b, stem)
            for stem, a, b in collisions
        ]
        return Result.fail(
            "Scatter file name collision: {}".format("; ".join(bits)),
            stage="scatter_names",
        )
    return Result.success(stage="scatter_names", data=stem_to_source)
