# -*- coding: utf-8 -*-
"""Point JSON 契約（schema_version=1；與 Camera 分通道）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from foundation.point_math import (
    display_name_from_layer,
    find_node_key_collisions,
    node_key_from_type_id,
    type_id_from_layer,
    xform_to_list,
)
from foundation.result import Result

SCHEMA_VERSION = 1
PRODUCER_RHINO = "r2o_rhino"
ALLOWED_KINDS = ("point", "block")


def _as_xform12(node: Any) -> Optional[List[float]]:
    if not isinstance(node, Sequence) or isinstance(node, (str, bytes)):
        return None
    if len(node) != 12:
        return None
    out = []
    for value in node:
        try:
            out.append(float(value))
        except (TypeError, ValueError):
            return None
    return out


def build_item(
    *,
    layer_full: str,
    kind: str,
    xform: Sequence[float],
    guid: str = "",
) -> Dict[str, Any]:
    type_id = type_id_from_layer(layer_full)
    return {
        "type_id": type_id,
        "display_name": display_name_from_layer(layer_full),
        "source_layer_path": type_id,
        "guid": str(guid or ""),
        "kind": str(kind),
        "node_key": node_key_from_type_id(type_id),
        "xform": xform_to_list(xform),
    }


def build_point_payload(
    items: Sequence[Mapping[str, Any]],
    *,
    producer: str = PRODUCER_RHINO,
    document_name: str = "",
    revision: int = 1,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "producer": producer,
        "document": document_name or "",
        "revision": int(revision),
        "items": list(items),
    }


def validate_point_payload(data: Any) -> Optional[str]:
    if not isinstance(data, Mapping):
        return "Point JSON root must be an object"
    try:
        ver = int(data.get("schema_version"))
    except (TypeError, ValueError):
        return "Missing or invalid schema_version"
    if ver != SCHEMA_VERSION:
        return "Unsupported schema_version: {} (need {})".format(ver, SCHEMA_VERSION)
    try:
        int(data.get("revision", 0))
    except (TypeError, ValueError):
        return "Field revision must be an integer"
    items = data.get("items")
    if not isinstance(items, list):
        return "Field items must be an array"
    type_ids = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            return "items[{}] must be an object".format(index)
        type_id = item.get("type_id")
        if not isinstance(type_id, str) or not type_id.strip():
            return "items[{}].type_id must be a non-empty string".format(index)
        if "\n" in type_id or "\r" in type_id:
            return "items[{}].type_id contains a newline".format(index)
        kind = item.get("kind")
        if kind not in ALLOWED_KINDS:
            return "items[{}].kind must be point or block".format(index)
        if _as_xform12(item.get("xform")) is None:
            return "items[{}].xform must be 12 numbers".format(index)
        type_ids.append(type_id)
    collisions = find_node_key_collisions(type_ids)
    if collisions:
        first = collisions[0]
        return "Node key collision for {} from {}".format(
            first["node_key"],
            " | ".join(first["type_ids"]),
        )
    return None


def parse_point_payload(data: Any) -> Result:
    err = validate_point_payload(data)
    if err:
        return Result.fail(err, stage="parse_point")
    assert isinstance(data, Mapping)
    return Result.success(stage="parse_point", data=data)


def validate_point_file(path) -> Optional[str]:
    try:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception as exc:
        return "Point pending could not be parsed: {}".format(exc)
    return validate_point_payload(data)
