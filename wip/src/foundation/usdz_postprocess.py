# -*- coding: utf-8 -*-
"""USDZ 材質 binding 後處理：把 Mesh 上的 rel material:binding 提升到圖層 Xform。"""
from __future__ import annotations

import io
import os
import re
import zipfile
from pathlib import Path
from typing import Optional, Tuple, Union

from foundation.result import Result

PathLike = Union[str, os.PathLike]

_PRIM_DEF = re.compile(r"^def\s+(\w+)\s+\"")
_BINDING = re.compile(r"rel\s+material:binding\s*=\s*(<[^>]+>)")


def find_ascii_usd_name(names) -> Optional[str]:
    """USDZ 內第一個 ASCII USD（.usda／.usd）。二進位 .usdc 不算。"""
    for name in names:
        lower = str(name).lower()
        if lower.endswith(".usda") or lower.endswith(".usd"):
            if not lower.endswith(".usdc"):
                return name
    return None


def promote_material_bindings_usda(raw: str) -> Tuple[str, int]:
    """
    若同一 Xform 下直接子 Mesh 共用同一個 binding，把該 rel 寫到 Xform 並刪 Mesh 列。

    回傳 (新 USDA 文字, 提升次數)。混合材質的 Xform 不改（與 1.x 相同）。
    """
    lines = raw.splitlines(keepends=True)
    stack = []
    insert_after = {}
    lines_to_drop = set()
    promoted = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        match = _PRIM_DEF.match(stripped)
        if match:
            prim_type = match.group(1)
            if prim_type == "Xform":
                kind = "Xform"
            elif prim_type == "Mesh":
                kind = "Mesh"
            else:
                kind = "other"
            stack.append(
                {
                    "type": kind,
                    "open_line": None,
                    "bindings": set(),
                    "child_bnd_lines": [],
                    "pending_open": True,
                }
            )

        if "{" in stripped and stack and stack[-1]["pending_open"]:
            stack[-1]["open_line"] = i
            stack[-1]["pending_open"] = False

        bm = _BINDING.search(stripped)
        if bm:
            for j in range(len(stack) - 1, -1, -1):
                if stack[j]["type"] == "Mesh":
                    stack[j]["bindings"].add(bm.group(1))
                    stack[j]["child_bnd_lines"].append(i)
                    break

        for _ in range(stripped.count("}")):
            if not stack:
                break
            frame = stack.pop()
            if frame["type"] == "Mesh" and len(frame["bindings"]) == 1:
                parent = next(
                    (f for f in reversed(stack) if f["type"] == "Xform"),
                    None,
                )
                if parent is not None:
                    parent["bindings"].update(frame["bindings"])
                    parent["child_bnd_lines"].extend(frame["child_bnd_lines"])
            elif (
                frame["type"] == "Xform"
                and len(frame["bindings"]) == 1
                and frame["open_line"] is not None
            ):
                binding = next(iter(frame["bindings"]))
                open_text = lines[frame["open_line"]]
                indent_match = re.match(r"^(\s*)", open_text)
                indent = (indent_match.group(1) if indent_match else "") + "    "
                insert_after[frame["open_line"]] = (binding, indent)
                lines_to_drop.update(frame["child_bnd_lines"])
                promoted += 1

    out = []
    for i, line in enumerate(lines):
        if i in lines_to_drop:
            continue
        out.append(line)
        if i in insert_after:
            binding, indent = insert_after[i]
            out.append("{}rel material:binding = {}\n".format(indent, binding))
    return "".join(out), promoted


def validate_usdz_file(path: PathLike) -> Optional[str]:
    """可讀 USDZ：非空 zip，且含 ASCII USD。失敗字串給 atomic validate。"""
    target = Path(path)
    if not target.is_file():
        return "USDZ is missing"
    if target.stat().st_size < 32:
        return "USDZ is too small"
    try:
        with zipfile.ZipFile(target, "r") as zf:
            names = zf.namelist()
    except zipfile.BadZipFile:
        return "USDZ is not a valid zip"
    if find_ascii_usd_name(names) is None:
        return "USDZ has no ASCII USD (usda) to verify material bindings"
    return None


def promote_material_bindings_usdz(usdz_path: PathLike) -> Result:
    """
    就地重打包 pending USDZ。找不到 ASCII USD 或例外＝整次失敗（R2O-ECO-03）。
    沒有可提升的 binding 仍算成功（場景可以沒有材質）。
    """
    path = Path(usdz_path)
    stage = "usdz_postprocess"
    if not path.is_file():
        return Result.fail("USDZ is missing: {}".format(path), stage=stage)

    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            usd_name = find_ascii_usd_name(names)
            if usd_name is None:
                return Result.fail(
                    "USDZ has no ASCII USD (usda) for material post-process",
                    stage=stage,
                )
            raw = zf.read(usd_name).decode("utf-8")
            others = {n: (zf.read(n), zf.getinfo(n)) for n in names if n != usd_name}
            usd_info = zf.getinfo(usd_name)

        new_content, promoted = promote_material_bindings_usda(raw)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zout:
            zout.writestr(zipfile.ZipInfo(usd_info.filename), new_content.encode("utf-8"))
            for fname, (fdata, finfo) in others.items():
                zout.writestr(zipfile.ZipInfo(finfo.filename), fdata)

        path.write_bytes(buf.getvalue())
        err = validate_usdz_file(path)
        if err:
            return Result.fail(err, stage="validate")
        return Result.success(
            "Promoted {} layer binding(s)".format(promoted),
            stage=stage,
            data={"path": str(path), "promoted": promoted},
        )
    except Exception as exc:
        return Result.fail("USDZ post-process failed: {}".format(exc), stage=stage)
