# -*- coding: utf-8 -*-
"""圖層子樹與排除記號（純邏輯；對齊 R2B）。"""
from __future__ import annotations

from typing import Iterable, Mapping, Sequence

DEFAULT_LAYER_EXCLUDE_TOKEN = "//"


def layer_path_is_excluded(
    full_path: str, exclude_token: str = DEFAULT_LAYER_EXCLUDE_TOKEN
) -> bool:
    """圖層 FullPath 含排除標記則不匯出。空白標記＝不排除。"""
    token = (exclude_token or "").strip()
    if not token:
        return False
    return token in (full_path or "")


def top_level_layer_paths(paths: Sequence[str]) -> tuple:
    """只留沒有 `::` 的最上層圖層。順序維持原清單。"""
    out = []
    seen = set()
    for path in paths:
        text = str(path or "").strip()
        if not text or "::" in text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return tuple(out)


def top_level_of(path: str) -> str:
    """子圖層路徑改回最上層名稱。空白回空字串。"""
    text = str(path or "").strip()
    if not text:
        return ""
    return text.split("::", 1)[0]


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


def layer_ids_with_ancestors(start_ids: Iterable, parent_by_id: Mapping) -> tuple:
    """起始圖層 id，加上每一層的父圖層。父層不在表內或成環就停。

    物件在子圖層、父圖層被鎖時，Rhino 仍不能選取該物件，所以要一併解開父層。
    Block 定義內幾何的圖層 id 由呼叫端放進 start_ids。
    """
    out = []
    seen = set()
    for start in start_ids:
        current = start
        while current is not None and current not in seen:
            seen.add(current)
            out.append(current)
            current = parent_by_id.get(current)
    return tuple(out)
