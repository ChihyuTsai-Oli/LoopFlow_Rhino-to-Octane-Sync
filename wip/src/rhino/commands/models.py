# -*- coding: utf-8 -*-
"""Rhino Models 通道：選圖層 → 匯出 pending USDZ → 材質後處理 → atomic。來源一律還原。"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from foundation.atomic import atomic_publish_from_pending
from foundation.log import append_log
from foundation.paths import (
    config_root_for_document,
    ensure_config_layout,
    models_path,
    pending_path_for,
    require_saved_document_path,
)
from foundation.pointer import write_current_project_pointer
from foundation.result import Result
from foundation.usdz_postprocess import (
    promote_material_bindings_usdz,
    validate_usdz_file,
)

_STICKY_LAST_LAYER = "R2O2_LAST_MODEL_LAYER"

_ALLOWED_TYPE_NAMES = (
    "Brep",
    "Extrusion",
    "Mesh",
    "SubD",
    "Surface",
    "InstanceReference",
)


def _sticky():
    import scriptcontext as sc  # type: ignore

    return sc.sticky


def _resolve_publish_target() -> Result:
    import scriptcontext as sc  # type: ignore

    doc = sc.doc
    path = getattr(doc, "Path", None) if doc else None
    saved = require_saved_document_path(path)
    if not saved.ok:
        return saved
    root = ensure_config_layout(config_root_for_document(saved.data))
    final = models_path(root)
    return Result.success(
        data={
            "root": root,
            "final": final,
            "pending": pending_path_for(final),
            "document": saved.data,
        },
        stage="resolve_path",
    )


def _prompt_layer(default_layer: Optional[str]) -> Optional[str]:
    import rhinoscriptsyntax as rs  # type: ignore

    return rs.GetLayer("Select the model layer to export", layer=default_layer)


def _layer_subtree_paths(doc, root_path: str):
    paths = set()
    prefix = root_path + "::"
    for layer in doc.Layers:
        if layer is None or layer.IsDeleted:
            continue
        fp = layer.FullPath
        if fp == root_path or fp.startswith(prefix):
            paths.add(fp)
    return paths


def _allowed_types():
    import Rhino  # type: ignore

    ot = Rhino.DocObjects.ObjectType
    mask = ot.Brep
    for name in _ALLOWED_TYPE_NAMES:
        if name == "Brep":
            continue
        mask = mask | getattr(ot, name)
    return mask


def _collect_export_ids(doc, target_paths) -> List:
    import Rhino  # type: ignore

    allowed = _allowed_types()
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.IncludeDeletedObjects = False
    settings.IncludeGrips = False
    settings.HiddenObjects = True
    settings.LockedObjects = True

    ids = []
    for obj in doc.Objects.GetObjectList(settings):
        if obj is None or obj.IsDeleted:
            continue
        try:
            layer_index = obj.Attributes.LayerIndex
            layer = doc.Layers[layer_index] if layer_index >= 0 else None
            layer_fp = layer.FullPath if layer else None
        except Exception:
            continue
        if not layer_fp or layer_fp not in target_paths:
            continue
        if (obj.ObjectType & allowed) == 0:
            continue
        ids.append(obj.Id)
    return ids


def _snapshot_and_prepare(doc, export_ids) -> Tuple[Dict, Dict, Dict, object, List]:
    """回傳 layer_state, obj_vislock, obj_matsrc, previous_modified, previous_selection。"""
    import rhinoscriptsyntax as rs  # type: ignore
    import Rhino  # type: ignore

    layer_state = {}
    for layer in doc.Layers:
        if layer is None or layer.IsDeleted:
            continue
        layer_state[layer.Id] = (layer.IsVisible, layer.IsLocked)

    obj_vislock = {}
    obj_matsrc = {}
    for obj_id in export_ids:
        obj = doc.Objects.FindId(obj_id)
        if obj is None:
            continue
        try:
            obj_vislock[obj_id] = (bool(obj.IsHidden), bool(obj.IsLocked))
        except Exception:
            obj_vislock[obj_id] = (False, False)
        try:
            obj_matsrc[obj_id] = obj.Attributes.MaterialSource
        except Exception:
            obj_matsrc[obj_id] = None

    previous_selection = list(rs.SelectedObjects() or [])
    previous_modified = bool(getattr(doc, "Modified", False))

    layer_from = Rhino.DocObjects.ObjectMaterialSource.MaterialFromLayer
    touched_layers = set()
    for obj_id in export_ids:
        obj = doc.Objects.FindId(obj_id)
        if obj is None:
            continue
        try:
            layer_index = obj.Attributes.LayerIndex
            if layer_index >= 0:
                touched_layers.add(doc.Layers[layer_index].Id)
        except Exception:
            pass
        try:
            doc.Objects.Unlock(obj_id, True)
        except Exception:
            pass
        try:
            doc.Objects.Show(obj_id, True)
        except Exception:
            pass
        try:
            attr = obj.Attributes
            if attr.MaterialSource != layer_from:
                attr.MaterialSource = layer_from
                obj.CommitChanges()
        except Exception:
            pass

    for layer in doc.Layers:
        if layer is None or layer.IsDeleted:
            continue
        if layer.Id not in touched_layers:
            continue
        changed = False
        if not layer.IsVisible:
            layer.IsVisible = True
            changed = True
        if layer.IsLocked:
            layer.IsLocked = False
            changed = True
        if changed:
            try:
                layer.CommitChanges()
            except Exception:
                pass

    return layer_state, obj_vislock, obj_matsrc, previous_modified, previous_selection


def _restore_document(
    doc,
    layer_state,
    obj_vislock,
    obj_matsrc,
    previous_modified,
    previous_selection,
) -> None:
    import rhinoscriptsyntax as rs  # type: ignore

    for obj_id, (was_hidden, was_locked) in obj_vislock.items():
        try:
            if was_locked:
                doc.Objects.Lock(obj_id, True)
            else:
                doc.Objects.Unlock(obj_id, True)
        except Exception:
            pass
        try:
            if was_hidden:
                doc.Objects.Hide(obj_id, True)
            else:
                doc.Objects.Show(obj_id, True)
        except Exception:
            pass

    for obj_id, source in obj_matsrc.items():
        if source is None:
            continue
        obj = doc.Objects.FindId(obj_id)
        if obj is None:
            continue
        try:
            attr = obj.Attributes
            if attr.MaterialSource != source:
                attr.MaterialSource = source
                obj.CommitChanges()
        except Exception:
            pass

    for layer in doc.Layers:
        if layer is None or layer.IsDeleted:
            continue
        st = layer_state.get(layer.Id)
        if not st:
            continue
        try:
            layer.IsVisible = st[0]
            layer.IsLocked = st[1]
            layer.CommitChanges()
        except Exception:
            pass

    try:
        rs.UnselectAllObjects()
        if previous_selection:
            rs.SelectObjects(previous_selection)
    except Exception:
        pass

    try:
        doc.Modified = previous_modified
    except Exception:
        pass


def _export_selected_usdz(export_ids, pending: Path) -> Result:
    import rhinoscriptsyntax as rs  # type: ignore

    pending.parent.mkdir(parents=True, exist_ok=True)
    if pending.exists():
        try:
            pending.unlink()
        except OSError as exc:
            return Result.fail(
                "Cannot clear pending USDZ: {}".format(exc),
                stage="export_usdz",
            )

    rs.UnselectAllObjects()
    rs.SelectObjects(export_ids)
    quote = chr(34)
    cmd = "_-Export " + quote + str(pending) + quote + " _Enter _Enter"
    rs.Command(cmd, False)
    if not pending.is_file() or pending.stat().st_size < 32:
        return Result.fail(
            "USDZ was not created. Check the path and Rhino USD export.",
            stage="export_usdz",
        )
    return Result.success(stage="export_usdz", data=str(pending))


def publish_models_once(*, layer: Optional[str] = None, interactive: bool = True) -> Result:
    """發布 `models/models.usdz`。取消／無物件不碰 last-good。"""
    import Rhino  # type: ignore
    import rhinoscriptsyntax as rs  # type: ignore

    target = _resolve_publish_target()
    if not target.ok:
        return target

    doc = Rhino.RhinoDoc.ActiveDoc
    if not doc:
        return Result.fail("No active document", stage="publish_models")

    sticky = _sticky()
    target_layer = layer
    if interactive and not target_layer:
        target_layer = _prompt_layer(sticky.get(_STICKY_LAST_LAYER))
        if not target_layer:
            return Result.blocked("Layer selection cancelled", stage="models_layer")
    if not target_layer:
        return Result.blocked("No model layer specified", stage="models_layer")

    subtree = _layer_subtree_paths(doc, target_layer)
    if not subtree:
        return Result.blocked(
            "Layer '{}' was not found".format(target_layer),
            stage="models_layer",
        )

    export_ids = _collect_export_ids(doc, subtree)
    if not export_ids:
        return Result.blocked(
            "No exportable geometry (Brep/Mesh/SubD/Block) in layer '{}'".format(
                target_layer
            ),
            stage="models_collect",
        )

    root = target.data["root"]
    final = target.data["final"]
    pending = target.data["pending"]
    snap = None
    rs.EnableRedraw(False)
    try:
        snap = _snapshot_and_prepare(doc, export_ids)
        exported = _export_selected_usdz(export_ids, pending)
        if not exported.ok:
            try:
                if pending.exists():
                    pending.unlink()
            except OSError:
                pass
            append_log(root, "Models publish: {} ({})".format(exported.status, exported.message))
            return exported

        promoted = promote_material_bindings_usdz(pending)
        if not promoted.ok:
            try:
                if pending.exists():
                    pending.unlink()
            except OSError:
                pass
            append_log(root, "Models publish: {} ({})".format(promoted.status, promoted.message))
            return promoted

        published = atomic_publish_from_pending(
            final, pending_path=pending, validate=validate_usdz_file
        )
        if published.ok:
            write_current_project_pointer(root, target.data["document"])
            sticky[_STICKY_LAST_LAYER] = target_layer
            message = "Published {} object(s) from '{}' → {}".format(
                len(export_ids), target_layer, final
            )
            published = Result.success(message, stage=published.stage, data=str(final))
        append_log(
            root,
            "Models publish: {} ({}); layer={}; count={}".format(
                published.status, published.message, target_layer, len(export_ids)
            ),
        )
        return published
    except Exception as exc:
        try:
            if pending.exists():
                pending.unlink()
        except OSError:
            pass
        fail = Result.fail("Models export failed: {}".format(exc), stage="publish_models")
        append_log(root, "Models publish: {} ({})".format(fail.status, fail.message))
        return fail
    finally:
        try:
            if snap is not None:
                _restore_document(doc, *snap)
        finally:
            rs.EnableRedraw(True)
