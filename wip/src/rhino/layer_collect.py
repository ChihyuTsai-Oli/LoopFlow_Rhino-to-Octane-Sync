# -*- coding: utf-8 -*-
"""圖層子樹與排除記號（純邏輯；對齊 R2B）。"""
from __future__ import annotations

from typing import Iterable, Sequence

DEFAULT_LAYER_EXCLUDE_TOKEN = "//"


def layer_path_is_excluded(
    full_path: str, exclude_token: str = DEFAULT_LAYER_EXCLUDE_TOKEN
) -> bool:
    """圖層 FullPath 含排除標記則不匯出。空白標記＝不排除。"""
    token = (exclude_token or "").strip()
    if not token:
        return False
    return token in (full_path or "")


def layer_subtree_paths(
    all_paths: Sequence[str],
    root: str,
    *,
    exclude_token: str = DEFAULT_LAYER_EXCLUDE_TOKEN,
) -> tuple:
    """回傳 root 與其子圖層 FullPath；略過含排除標記者。"""
    root = (root or "").strip()
    if not root:
        return ()
    if layer_path_is_excluded(root, exclude_token):
        return ()
    prefix = root + "::"
    out = []
    for path in all_paths:
        if path is None:
            continue
        p = str(path)
        if layer_path_is_excluded(p, exclude_token):
            continue
        if p == root or p.startswith(prefix):
            out.append(p)
    return tuple(out)


def kind_is_included(
    kind: str,
    include_kinds: Iterable[str],
) -> bool:
    wanted = {str(k).lower() for k in include_kinds}
    return str(kind or "other").lower() in wanted
