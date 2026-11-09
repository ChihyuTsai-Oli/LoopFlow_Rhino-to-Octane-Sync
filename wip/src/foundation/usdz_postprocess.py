# -*- coding: utf-8 -*-
"""USDZ 材質 binding 後處理：把 Mesh 上的 rel material:binding 提升到圖層 Xform。"""
from __future__ import annotations

import io
import os
import re
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

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


def usd_material_prefix(layer_full_path: str) -> str:
    """Rhino 8 把圖層路徑的 `::` 寫成 `__`，接在 `material_` 後面。"""
    return "material_" + str(layer_full_path).replace("::", "__")


def _ascii_usd_piece(text: str) -> str:
    """只留英文、數字與底線。中文、`.` 與連字號改成 `_`，不刪底線。"""
    out = []
    for ch in str(text):
        if ("0" <= ch <= "9") or ("A" <= ch <= "Z") or ("a" <= ch <= "z") or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)


def _sanitize_usd_token(text: str) -> str:
    return _ascii_usd_piece(text).strip("_")


def stable_material_prim(material_name: str, layer_path: str) -> Tuple[str, str]:
    """
    回傳 (來源鍵, prim 名)。

    有材質名稱時，同名共用一個 prim。名稱空白時用圖層路徑，避免無名材質被併在一起。
    """
    source = (material_name or "").strip()
    if source:
        key = "name:" + source
        token = _sanitize_usd_token(source)
    else:
        key = "layer:" + layer_path
        token = _ascii_usd_piece(str(layer_path).replace("::", "_"))
    if not token:
        token = "unnamed"
    if token[0].isdigit():
        token = "m_" + token
    return key, "material_" + token


def layer_to_stable_prims(layer_materials: Dict[str, str]) -> Dict[str, str]:
    """圖層完整路徑 → 穩定 Material prim 名。不同來源洗成同名時加 _2、_3。"""
    key_desired = {}
    layer_key = {}
    for path, mat_name in layer_materials.items():
        key, prim = stable_material_prim(mat_name, path)
        layer_key[path] = key
        key_desired[key] = prim

    key_prim = {}
    used = set()
    for key in sorted(key_desired):
        base = key_desired[key]
        prim = base
        suffix = 2
        while prim in used:
            prim = "{}_{}".format(base, suffix)
            suffix += 1
        used.add(prim)
        key_prim[key] = prim
    return {path: key_prim[layer_key[path]] for path in layer_materials}


_HEX_TAIL = re.compile(r"(?:_[0-9A-Fa-f]{3,8}){4}$")


def strip_material_tail(prim_name: str) -> str:
    """去掉結尾四段十六進位。圖層路徑留下，幾何變動不會改這條名字。"""
    stripped = _HEX_TAIL.sub("", prim_name)
    if not stripped or stripped == prim_name:
        return prim_name
    return stripped


_EMPTY_GUID = "00000000-0000-0000-0000-000000000000"


def normalize_guid_text(value) -> Optional[str]:
    """圖層 Id 正規成小寫、無大括號。空 Id 回 None。"""
    if value is None:
        return None
    text = str(value).strip().strip("{}").lower()
    if not text or text == _EMPTY_GUID:
        return None
    return text


def layer_export_token(layer_id) -> str:
    """匯出當下的圖層代號。同一圖層每次都一樣，且不會跟別層撞名。"""
    text = normalize_guid_text(layer_id)
    if not text:
        raise ValueError("Layer id is empty")
    hexed = text.replace("-", "").upper()
    if len(hexed) != 32 or any(ch not in "0123456789ABCDEF" for ch in hexed):
        raise ValueError("Layer id is not a GUID")
    return "LF" + hexed


def usd_xform_name(name: str) -> str:
    """
    圖層名換成 USD 節點名。

    只用英文、數字與底線。中文與 `.` 改成 `_`，不刪底線。
    以數字開頭時前面加 `_`。Octane 不接受中文節點名，否則不會建立材質接口。
    """
    token = _ascii_usd_piece(name)
    if not token:
        token = "layer"
    if token[0].isdigit():
        token = "_" + token
    return token


def plan_layer_export(rows) -> Dict[str, Dict[str, str]]:
    """
    由 (圖層 Id, 名稱, 完整路徑, 父 Id) 產生匯出計畫。

    `renames`：正規化 Id → 代號。`path_alias`：代號完整路徑 → 原完整路徑。
    `prim_names`：代號 → USD 節點名。末端圖層用父層名加自己的名字，
    因為 Rhino 把末端放在最外面，不同父層的同名子圖層會變成兄弟。
    加完仍然相同才加 `_2`。
    """
    by_id = {}
    for layer_id, name, full_path, parent_id in rows:
        lid = normalize_guid_text(layer_id)
        if not lid:
            continue
        parent = normalize_guid_text(parent_id)
        by_id[lid] = (str(name), str(full_path), parent)

    tokens = {lid: layer_export_token(lid) for lid in by_id}

    def _token_path(lid: str) -> str:
        parts = []
        seen = set()
        cur = lid
        while cur and cur not in seen and cur in by_id:
            seen.add(cur)
            parts.append(tokens[cur])
            cur = by_id[cur][2]
        parts.reverse()
        return "::".join(parts)

    path_alias = {_token_path(lid): by_id[lid][1] for lid in by_id}

    children = {}
    for lid, (_name, _full, parent) in by_id.items():
        children.setdefault(parent, []).append(lid)

    prim_names = {}
    for _parent, ids in children.items():
        used = set()
        for lid in sorted(ids, key=lambda item: by_id[item][1]):
            base = usd_xform_name(by_id[lid][0])
            prim = base
            suffix = 2
            while prim in used:
                prim = "{}_{}".format(base, suffix)
                suffix += 1
            used.add(prim)
            prim_names[tokens[lid]] = prim

    is_parent = {parent for (_name, _full, parent) in by_id.values() if parent in by_id}
    used_leaves = set()
    for lid in sorted(
        (item for item in by_id if item not in is_parent),
        key=lambda item: by_id[item][1],
    ):
        child = usd_xform_name(by_id[lid][0])
        parent = by_id[lid][2]
        if parent in by_id:
            base = usd_xform_name(by_id[parent][0]) + child
        else:
            base = child
        prim = base
        suffix = 2
        while prim in used_leaves:
            prim = "{}_{}".format(base, suffix)
            suffix += 1
        used_leaves.add(prim)
        prim_names[tokens[lid]] = prim

    return {
        "path_alias": path_alias,
        "prim_names": prim_names,
        "renames": {lid: tokens[lid] for lid in by_id},
    }


def apply_layer_prim_names(raw: str, prim_names: Optional[Dict[str, str]] = None) -> str:
    """把匯出代號換回圖層節點名。材質 prim 應已先改完，這裡不再碰到它們。"""
    if not prim_names:
        return raw
    text = raw
    for token, name in sorted(prim_names.items(), key=lambda item: len(item[0]), reverse=True):
        if token and token != name:
            text = text.replace(token, name)
    return text


def match_layer_for_material_prim(
    prim_name: str, layer_materials: Dict[str, str]
) -> Optional[str]:
    """最長圖層前綴對上的圖層。對不到回 None，呼叫端保留原 prim。"""
    return match_exported_material_layer(prim_name, layer_materials, None)


def match_exported_material_layer(
    prim_name: str,
    layer_materials: Dict[str, str],
    path_alias: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    最長前綴對上的原圖層路徑。

    `path_alias` 是 Rhino 這次實際寫出的路徑（代號）→ 原完整路徑。
    只接受對照表裡有的原路徑，避免父層前綴吃掉子層。
    """
    best_path = None
    best_len = -1
    pairs = [(path, path) for path in layer_materials]
    for written, original in (path_alias or {}).items():
        pairs.append((written, original))
    for written, original in pairs:
        if original not in layer_materials:
            continue
        prefix = usd_material_prefix(written)
        if _prefix_matches_material_prim(prim_name, prefix):
            if len(prefix) > best_len:
                best_path = original
                best_len = len(prefix)
    return best_path


def _prefix_matches_material_prim(prim_name: str, prefix: str) -> bool:
    """前綴後面只能是整段十六進位尾碼，不能把尾碼的底線當成圖層名。"""
    if prim_name == prefix:
        return True
    if not prim_name.startswith(prefix):
        return False
    return _HEX_TAIL.fullmatch(prim_name[len(prefix) :]) is not None


def _material_blocks(lines):
    """每個 `def Material` 區塊的起迄行（含首尾）。"""
    blocks = []
    depth = 0
    current = None
    mat_def = re.compile(r'^def\s+Material\s+"([^"]+)"')
    for i, line in enumerate(lines):
        stripped = line.strip()
        opens = stripped.count("{")
        closes = stripped.count("}")
        match = mat_def.match(stripped)
        if match and current is None:
            current = {
                "name": match.group(1),
                "start": i,
                "base": depth,
                "opened": False,
            }
        if current is not None and opens:
            current["opened"] = True
        new_depth = depth + opens - closes
        if (
            current is not None
            and current["opened"]
            and new_depth <= current["base"]
        ):
            current["end"] = i
            blocks.append(current)
            current = None
        depth = new_depth
    return blocks


def _rewrite_material_block(block_text: str, old: str, new: str) -> str:
    text = block_text.replace(
        'def Material "{}"'.format(old),
        'def Material "{}"'.format(new),
        1,
    )
    text = re.sub(r'def Shader "[^"]+"', 'def Shader "surface"', text, count=1)
    text = re.sub(
        r"/Rhino/Materials/{}/shader\d+".format(re.escape(old)),
        "/Rhino/Materials/{}/surface".format(new),
        text,
    )
    text = text.replace(
        "/Rhino/Materials/{}".format(old),
        "/Rhino/Materials/{}".format(new),
    )
    return text


def rewrite_material_prims(
    raw: str,
    layer_materials: Optional[Dict[str, str]] = None,
    path_alias: Optional[Dict[str, str]] = None,
) -> Tuple[str, int]:
    """
    把 Material prim、Shader 與 binding 改成不隨幾何變動的路徑。

    對得到圖層時用 Rhino 材質名稱；名稱空白則用原圖層完整路徑。
    `path_alias` 讓代號路徑對回原路徑。對不到就只去掉十六進位尾碼。
    每個 Material 的 Shader 都改叫 `surface`。同名只留第一份。
    """
    layer_materials = layer_materials or {}
    layer_prims = layer_to_stable_prims(layer_materials) if layer_materials else {}
    lines = raw.splitlines(keepends=True)
    blocks = _material_blocks(lines)
    rename = {}
    seen_new = set()
    drop = set()
    for block in blocks:
        layer = (
            match_exported_material_layer(block["name"], layer_materials, path_alias)
            if layer_materials
            else None
        )
        if layer is not None:
            new_name = layer_prims[layer]
        else:
            new_name = strip_material_tail(block["name"])
        rename[block["name"]] = new_name
        if new_name in seen_new:
            drop.add(block["start"])
            continue
        seen_new.add(new_name)
        block["rewrite"] = new_name

    if not blocks:
        return raw, 0

    out = []
    index = 0
    rewritten = {b["start"]: b for b in blocks if b.get("rewrite")}
    skipped = {b["start"]: b for b in blocks if b["start"] in drop}
    while index < len(lines):
        if index in skipped:
            index = skipped[index]["end"] + 1
            continue
        if index in rewritten:
            block = rewritten[index]
            chunk = "".join(lines[block["start"] : block["end"] + 1])
            out.append(_rewrite_material_block(chunk, block["name"], block["rewrite"]))
            index = block["end"] + 1
            continue
        out.append(lines[index])
        index += 1

    text = "".join(out)
    pairs = [(old, new) for old, new in rename.items() if old != new]
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    for old, new in pairs:
        text = text.replace(
            "/Rhino/Materials/{}".format(old),
            "/Rhino/Materials/{}".format(new),
        )
    changed = sum(1 for old, new in rename.items() if old != new)
    return text, changed


def _token_layer_paths(
    path_alias: Optional[Dict[str, str]],
    layer_materials: Dict[str, str],
) -> Dict[str, str]:
    """代號 → 原圖層路徑。只留這次有匯出材質的圖層。"""
    found = {}
    for written, original in (path_alias or {}).items():
        token = str(written).split("::")[-1]
        if token and original in layer_materials:
            found[token] = original
    return found


def _blank_material_block(name: str, indent: str) -> str:
    inner = indent + "    "
    shader = inner + "    "
    return (
        '{0}def Material "{1}"\n'
        "{0}{{\n"
        "{2}token outputs:surface.connect = </Rhino/Materials/{1}/surface.outputs:surface>\n"
        '{2}def Shader "surface"\n'
        "{2}{{\n"
        '{3}uniform token info:id = "UsdPreviewSurface"\n'
        "{2}}}\n"
        "{0}}}\n"
    ).format(indent, name, inner, shader)


def _referenced_materials(text: str) -> set:
    return set(
        re.findall(
            r"rel\s+material:binding\s*=\s*</Rhino/Materials/([^/>]+)>",
            text,
        )
    )


def _materials_scope_end(lines) -> Optional[int]:
    start = None
    for index, line in enumerate(lines):
        if re.search(r'def\s+"Materials"', line):
            start = index
            break
    if start is None:
        return None
    depth = 0
    started = False
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if "{" in stripped:
            depth += stripped.count("{")
            started = True
        if stripped and set(stripped) == {"}"}:
            depth -= len(stripped)
            if started and depth <= 0:
                return index
    return None


def _sync_material_defs(
    text: str,
    needed: set,
    clones: Optional[Dict[str, str]] = None,
) -> str:
    """接線用到的 Material 要有定義；沒人接的舊定義拿掉。

    缺的定義從原本的區塊複製（含 shader）。找不到來源才補空的 UsdPreviewSurface。
    `clones` 是新 prim 名 → 複製來源的 prim 名。
    """
    if not needed:
        return text
    clones = clones or {}
    lines = text.splitlines(keepends=True)
    blocks = _material_blocks(lines)
    referenced = _referenced_materials(text)
    by_name = {}
    for block in blocks:
        by_name.setdefault(block["name"], block)
    drop = {block["start"] for block in blocks if block["name"] not in referenced}
    kept = {block["name"] for block in blocks if block["name"] in referenced}
    indent = "        "
    for line in lines:
        if 'def Material "' in line:
            indent = re.match(r"^(\s*)", line).group(1)
            break
    missing = sorted(name for name in needed if name in referenced and name not in kept)
    pieces = []
    for name in missing:
        source = by_name.get(clones.get(name))
        if source is None:
            pieces.append(_blank_material_block(name, indent))
            continue
        chunk = "".join(lines[source["start"] : source["end"] + 1])
        pieces.append(_rewrite_material_block(chunk, source["name"], name))
    out = []
    index = 0
    skipped = {block["start"]: block for block in blocks if block["start"] in drop}
    while index < len(lines):
        if index in skipped:
            index = skipped[index]["end"] + 1
            continue
        out.append(lines[index])
        index += 1
    if not pieces:
        return "".join(out)
    insert_at = _materials_scope_end(out)
    block_text = "".join(pieces)
    if insert_at is None:
        return "".join(out) + block_text
    out.insert(insert_at, block_text)
    return "".join(out)


def assign_materials_from_leaf_layers(
    raw: str,
    path_alias: Optional[Dict[str, str]] = None,
    layer_materials: Optional[Dict[str, str]] = None,
) -> Tuple[str, int]:
    """
    依最外層圖層代號改接線。

    Rhino 把末端圖層放在最外面。材質 prim 若已被較長的名稱併走，
    仍用這顆代號對回原圖層，接到該層自己的接口。
    """
    layer_materials = layer_materials or {}
    token_layer = _token_layer_paths(path_alias, layer_materials)
    if not token_layer:
        return raw, 0
    layer_prims = layer_to_stable_prims(layer_materials)
    lines = raw.splitlines(keepends=True)
    stack = []
    pending = None
    changed = 0
    needed = set()
    clones = {}
    binding_name = re.compile(
        r"(rel\s+material:binding\s*=\s*</Rhino/Materials/)([^/>]+)(>)"
    )
    xform_name = re.compile(r'^def\s+Xform\s+"([^"]+)"')
    for index, line in enumerate(lines):
        stripped = line.strip()
        xform = xform_name.match(stripped)
        if xform:
            pending = xform.group(1)
        elif stripped.startswith("def "):
            pending = ""
        if pending is not None and "{" in stripped:
            stack.append(pending)
            pending = None
        found = binding_name.search(line)
        if found:
            leaf = next((name for name in stack if name in token_layer), None)
            if leaf is not None:
                prim = layer_prims.get(token_layer[leaf])
                if prim:
                    needed.add(prim)
                    if found.group(2) != prim:
                        clones.setdefault(prim, found.group(2))
                        line = binding_name.sub(
                            lambda match, prim=prim: match.group(1) + prim + match.group(3),
                            line,
                            count=1,
                        )
                        lines[index] = line
                        changed += 1
        if stripped and set(stripped) == {"}"}:
            for _ in stripped:
                if stack:
                    stack.pop()
            pending = None
    text = _sync_material_defs("".join(lines), needed, clones)
    return text, changed


def payload_name_for_final(final_path: PathLike) -> str:
    """zip 內 ASCII USD 檔名＝正式檔 stem，不要留下 `_pending`（對齊 1.x）。"""
    return "{}.usda".format(Path(final_path).stem)


def promote_material_bindings_usdz(
    usdz_path: PathLike,
    *,
    payload_name: Optional[str] = None,
    layer_materials: Optional[Dict[str, str]] = None,
    path_alias: Optional[Dict[str, str]] = None,
    layer_prim_names: Optional[Dict[str, str]] = None,
) -> Result:
    """
    就地重打包 pending USDZ。找不到 ASCII USD 或例外＝整次失敗（R2O-ECO-03）。
    沒有可提升的 binding 仍算成功（場景可以沒有材質）。
    `payload_name` 有值時，把 zip 內 USDA 改成該名（例如 `R2O.usda`）。
    `layer_materials` 是原圖層完整路徑 → Rhino 材質名稱。
    `path_alias` 是這次匯出寫出的代號路徑 → 原完整路徑。
    `layer_prim_names` 是代號 → 圖層節點名；材質改完後才套用。
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

        new_content, promoted = promote_material_bindings_usda(raw)
        new_content, renamed = rewrite_material_prims(
            new_content, layer_materials, path_alias
        )
        new_content, _rebound = assign_materials_from_leaf_layers(
            new_content, path_alias, layer_materials
        )
        new_content = apply_layer_prim_names(new_content, layer_prim_names)
        inner = payload_name or usd_name

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zout:
            zout.writestr(zipfile.ZipInfo(inner), new_content.encode("utf-8"))
            for fname, (fdata, finfo) in others.items():
                if fname == inner:
                    continue
                zout.writestr(zipfile.ZipInfo(finfo.filename), fdata)

        path.write_bytes(buf.getvalue())
        err = validate_usdz_file(path)
        if err:
            return Result.fail(err, stage="validate")
        return Result.success(
            "Promoted {} layer binding(s)".format(promoted),
            stage=stage,
            data={"path": str(path), "promoted": promoted, "renamed": renamed},
        )
    except Exception as exc:
        return Result.fail("USDZ post-process failed: {}".format(exc), stage=stage)
