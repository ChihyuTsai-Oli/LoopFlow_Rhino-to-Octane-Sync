# -*- coding: utf-8 -*-
"""Rhino Models 通道：R2B 同型三步視窗 → pending USDZ → 材質後處理 → atomic。"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from foundation.atomic import atomic_publish_from_pending
from foundation.export_cmd import rhino_export_target
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
    normalize_guid_text,
    payload_name_for_final,
    plan_layer_export,
    promote_material_bindings_usdz,
    validate_usdz_file,
)
from rhino.layer_collect import (
    DEFAULT_LAYER_EXCLUDE_TOKEN,
    kind_is_included,
    layer_ids_with_ancestors,
    layer_path_is_excluded,
    layer_subtree_paths,
)

_STICKY_LAST_LAYER = "R2O2_LAST_MODEL_LAYER"
_STICKY_EXCLUDE_TOKEN = "R2O2_LAYER_EXCLUDE_TOKEN"
_STICKY_LAST_TYPES = "R2O2_LAST_MODEL_TYPES"

# (顯示名, 預設勾選, 對應 kind 集合) — 對齊 R2B
_TYPE_ROWS: Tuple[Tuple[str, bool, Set[str]], ...] = (
    ("Point", False, {"point"}),
    ("Curve", False, {"curve"}),
    ("Brep / Polysurface / Surface", True, {"brep", "polysurface", "surface"}),
    ("Mesh", True, {"mesh"}),
    ("SubD", True, {"subd"}),
    ("Extrusion", True, {"extrusion"}),
    ("Block / Instance", True, {"block", "instance"}),
    ("Other", True, {"other"}),
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


def _all_layer_paths(doc) -> List[str]:
    out = []
    for layer in doc.Layers:
        if layer is None or layer.IsDeleted:
            continue
        fp = getattr(layer, "FullPath", None)
        if fp:
            out.append(str(fp))
    return out


def _prompt_exclude_token(default_token: str) -> Optional[str]:
    import rhinoscriptsyntax as rs  # type: ignore

    seed = default_token if default_token is not None else DEFAULT_LAYER_EXCLUDE_TOKEN
    value = rs.StringBox(
        message="Layer paths containing this text are skipped (blank = none)",
        default_value=seed,
        title="ROModels — Exclude Token",
    )
    if value is None:
        return None
    return str(value)


def _prompt_layer(doc, default_layer: Optional[str], exclude_token: str) -> Optional[str]:
    from rhino.ui.layer_picker import pick_layer_path

    paths = [
        p
        for p in _all_layer_paths(doc)
        if not layer_path_is_excluded(str(p), exclude_token)
    ]
    return pick_layer_path(
        paths,
        default_path=default_layer,
        title="ROModels",
        message="Select the model layer (includes sublayers)",
    )


def checklist_defaults(last_labels: Optional[Sequence[str]] = None) -> List[Tuple[str, bool]]:
    """回傳 (列標籤, 是否勾選)。無紀錄時用 _TYPE_ROWS 預設。"""
    last_set = None if last_labels is None else set(last_labels)
    rows: List[Tuple[str, bool]] = []
    for label, default, _kinds in _TYPE_ROWS:
        checked = default if last_set is None else (label in last_set)
        rows.append((label, checked))
    return rows


def _object_kind(obj, Rhino) -> str:
    ot = obj.ObjectType
    mapping = (
        ("Point", "point"),
        ("Curve", "curve"),
        ("Mesh", "mesh"),
        ("SubD", "subd"),
        ("Extrusion", "extrusion"),
        ("InstanceReference", "instance"),
        ("Surface", "surface"),
        ("Brep", "brep"),
    )
    for name, kind in mapping:
        flag = getattr(Rhino.DocObjects.ObjectType, name, None)
        if flag is not None and (ot & flag):
            if name == "Brep":
                try:
                    geom = obj.Geometry
                    if geom is not None and getattr(geom, "Faces", None) is not None:
                        if geom.Faces.Count > 1:
                            return "polysurface"
                except Exception:
                    pass
            return kind
    return "other"


def _count_kinds_under_layer(doc, subtree: Sequence[str]) -> Dict[str, int]:
    import Rhino  # type: ignore

    target = set(subtree)
    counts: Dict[str, int] = {}
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.IncludeDeletedObjects = False
    settings.IncludeGrips = False
    settings.HiddenObjects = True
    settings.LockedObjects = True
    for obj in doc.Objects.GetObjectList(settings):
        if obj is None or obj.IsDeleted:
            continue
        try:
            layer_index = obj.Attributes.LayerIndex
            layer = doc.Layers[layer_index] if layer_index >= 0 else None
            layer_fp = layer.FullPath if layer else None
        except Exception:
            continue
        if not layer_fp or layer_fp not in target:
            continue
        kind = _object_kind(obj, Rhino)
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _prompt_type_flags(doc, subtree: Sequence[str], last_labels: Optional[Sequence[str]] = None) -> Result:
    import rhinoscriptsyntax as rs  # type: ignore

    counts = _count_kinds_under_layer(doc, subtree)
    checklist: List[Tuple[str, bool]] = []
    row_kinds: List[Set[str]] = []
    labels: List[str] = []
    for label, checked in checklist_defaults(last_labels):
        kinds = next(k for lab, _d, k in _TYPE_ROWS if lab == label)
        n = sum(counts.get(k, 0) for k in kinds)
        checklist.append(("[{}] {}".format(n, label), checked))
        row_kinds.append(kinds)
        labels.append(label)

    chosen = rs.CheckListBox(
        checklist,
        message="Select geometry types to export",
        title="ROModels",
    )
    if chosen is None:
        return Result.blocked("Geometry type selection cancelled", stage="models_types")

    include: Set[str] = set()
    selected_labels: List[str] = []
    for (label, (_shown, checked), kinds) in zip(labels, chosen, row_kinds):
        if checked:
            include.update(kinds)
            selected_labels.append(label)
    if not include:
        return Result.blocked("No geometry types selected", stage="models_types")
    return Result.success(
        stage="models_types",
        data={"include": include, "labels": selected_labels},
    )


def _collect_export_ids(doc, target_paths, include_kinds: Iterable[str]) -> List:
    import Rhino  # type: ignore

    target = set(target_paths)
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
        if not layer_fp or layer_fp not in target:
            continue
        if not kind_is_included(_object_kind(obj, Rhino), include_kinds):
            continue
        ids.append(obj.Id)
    return ids


def _empty_layer_parent(layer) -> bool:
    parent_id = getattr(layer, "ParentLayerId", None)
    if parent_id is None:
        return True
    return str(parent_id).strip("{}").lower() == "00000000-0000-0000-0000-000000000000"


def _layer_id_of(doc, obj):
    try:
        index = int(obj.Attributes.LayerIndex)
    except Exception:
        return None
    if index < 0:
        return None
    try:
        layer = doc.Layers[index]
    except Exception:
        return None
    if layer is None or layer.IsDeleted:
        return None
    return layer.Id


def _append_block_member_layers(doc, obj, starts: List, seen_defs: Set, Rhino) -> None:
    """Block 不炸開。定義內幾何若在鎖定圖層，匯出前仍要解開那些圖層。"""
    try:
        flag = Rhino.DocObjects.ObjectType.InstanceReference
        if not (obj.ObjectType & flag):
            return
        idef_id = obj.Geometry.ParentIdefId
    except Exception:
        return
    if idef_id in seen_defs:
        return
    seen_defs.add(idef_id)
    try:
        idef = doc.InstanceDefinitions.FindId(idef_id)
        members = list(idef.GetObjects()) if idef is not None else []
    except Exception:
        return
    for member in members:
        if member is None:
            continue
        layer_id = _layer_id_of(doc, member)
        if layer_id is not None:
            starts.append(layer_id)
        _append_block_member_layers(doc, member, starts, seen_defs, Rhino)


def _layer_of_object(doc, obj):
    try:
        index = int(obj.Attributes.LayerIndex)
    except Exception:
        return None
    if index < 0:
        return None
    try:
        layer = doc.Layers[index]
    except Exception:
        return None
    if layer is None or getattr(layer, "IsDeleted", False):
        return None
    return layer


def _layer_material_name(doc, layer) -> str:
    """圖層材質名稱。沒有指定材質時回空白，後處理改用圖層路徑。"""
    try:
        index = int(layer.RenderMaterialIndex)
    except Exception:
        return ""
    if index < 0:
        return ""
    try:
        mat = doc.Materials[index]
    except Exception:
        return ""
    if mat is None:
        return ""
    return str(getattr(mat, "Name", "") or "")


def _remember_layer_material(doc, layer, found: Dict[str, str]) -> None:
    if layer is None:
        return
    path = getattr(layer, "FullPath", None)
    if not path or path in found:
        return
    found[path] = _layer_material_name(doc, layer)


def _remember_block_member_materials(doc, obj, found: Dict[str, str], seen_defs: Set) -> None:
    """Block 不炸開。定義內幾何的圖層材質也要進對照表，USD 才對得到。"""
    import Rhino  # type: ignore

    try:
        flag = Rhino.DocObjects.ObjectType.InstanceReference
        if not (obj.ObjectType & flag):
            return
        idef_id = obj.Geometry.ParentIdefId
    except Exception:
        return
    if idef_id in seen_defs:
        return
    seen_defs.add(idef_id)
    try:
        idef = doc.InstanceDefinitions.FindId(idef_id)
        members = list(idef.GetObjects()) if idef is not None else []
    except Exception:
        return
    for member in members:
        if member is None:
            continue
        _remember_layer_material(doc, _layer_of_object(doc, member), found)
        _remember_block_member_materials(doc, member, found, seen_defs)


def layer_material_names(doc, export_ids) -> Dict[str, str]:
    """匯出物件（含 block 定義內幾何）的圖層完整路徑 → 圖層材質名稱。"""
    found: Dict[str, str] = {}
    seen_defs: Set = set()
    for obj_id in export_ids:
        obj = doc.Objects.FindId(obj_id)
        if obj is None:
            continue
        _remember_layer_material(doc, _layer_of_object(doc, obj), found)
        _remember_block_member_materials(doc, obj, found, seen_defs)
    return found


def _layer_ids_to_unlock(doc, export_ids) -> List:
    import Rhino  # type: ignore

    parent_by_id = {}
    for layer in doc.Layers:
        if layer is None or layer.IsDeleted:
            continue
        parent_by_id[layer.Id] = None if _empty_layer_parent(layer) else layer.ParentLayerId

    starts = []
    seen_defs: Set = set()
    for obj_id in export_ids:
        obj = doc.Objects.FindId(obj_id)
        if obj is None:
            continue
        layer_id = _layer_id_of(doc, obj)
        if layer_id is not None:
            starts.append(layer_id)
        _append_block_member_layers(doc, obj, starts, seen_defs, Rhino)
    return list(layer_ids_with_ancestors(starts, parent_by_id))


def _modify_layers(doc, indexes, apply) -> None:
    """先記下索引再改，避免邊走圖層表邊 CommitChanges。"""
    for index in indexes:
        layer = doc.Layers[index]
        if layer is None or layer.IsDeleted:
            continue
        if not apply(layer):
            continue
        ok = doc.Layers.Modify(layer, index, True)
        if not ok:
            raise RuntimeError("Could not update layer index {}".format(index))


def _layer_indexes(doc, wanted_ids) -> List[int]:
    wanted = set(wanted_ids)
    indexes = []
    for layer in doc.Layers:
        if layer is None or layer.IsDeleted:
            continue
        if layer.Id in wanted:
            indexes.append(int(layer.Index))
    return indexes


_autosave_enabled = None


def _layer_own_state(layer):
    """圖層自己的可見／鎖定，不含父層連動。"""
    try:
        visible = bool(layer.GetPersistentVisibility())
    except Exception:
        visible = bool(layer.IsVisible)
    try:
        locked = bool(layer.GetPersistentLocking())
    except Exception:
        locked = bool(layer.IsLocked)
    return visible, locked, layer.Name


def _suspend_autosave() -> None:
    """匯出會暫時改圖層。這段關掉自動存檔，避免寫進回復檔。"""
    global _autosave_enabled
    if _autosave_enabled is not None:
        return
    try:
        import Rhino  # type: ignore

        settings = Rhino.ApplicationSettings.FileSettings
        previous = bool(settings.AutoSaveEnabled)
        settings.AutoSaveEnabled = False
        _autosave_enabled = previous
    except Exception:
        _autosave_enabled = None


def _resume_autosave() -> None:
    global _autosave_enabled
    previous = _autosave_enabled
    _autosave_enabled = None
    if previous is None:
        return
    try:
        import Rhino  # type: ignore

        Rhino.ApplicationSettings.FileSettings.AutoSaveEnabled = bool(previous)
    except Exception:
        pass


def _capture_export_state(doc, export_ids) -> Tuple[Dict, Dict, Dict, object, List]:
    """回傳 layer_state, obj_vislock, obj_matsrc, previous_modified, previous_selection。"""
    import rhinoscriptsyntax as rs  # type: ignore

    layer_state = {}
    for layer in doc.Layers:
        if layer is None or layer.IsDeleted:
            continue
        layer_state[layer.Id] = _layer_own_state(layer)

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
    return layer_state, obj_vislock, obj_matsrc, previous_modified, previous_selection


def _rename_export_layers(doc, export_ids) -> Dict[str, Dict[str, str]]:
    """
    會進 USD 的圖層暫時改成不重複代號。

    回傳 path_alias／prim_names／renames。呼叫端必須已先記下原名，結束時還原。
    """
    wanted = set(_layer_ids_to_unlock(doc, export_ids))
    rows = []
    indexes = []
    for layer in doc.Layers:
        if layer is None or layer.IsDeleted or layer.Id not in wanted:
            continue
        parent = None if _empty_layer_parent(layer) else layer.ParentLayerId
        rows.append((layer.Id, layer.Name, layer.FullPath, parent))
        indexes.append(int(layer.Index))
    plan = plan_layer_export(rows)
    renames = plan["renames"]

    def _apply(layer) -> bool:
        token = renames.get(normalize_guid_text(layer.Id))
        if not token or layer.Name == token:
            return False
        layer.Name = token
        return True

    _modify_layers(doc, indexes, _apply)
    return plan


def _prepare_export_visibility(doc, export_ids) -> Dict[str, Dict[str, str]]:
    """圖層先解鎖（含父層與 block 定義內圖層），改成代號，再解鎖物件。失敗留給還原。"""
    import Rhino  # type: ignore

    _suspend_autosave()
    unlock_ids = _layer_ids_to_unlock(doc, export_ids)

    def _show_and_unlock(layer) -> bool:
        changed = False
        if not layer.IsVisible:
            layer.IsVisible = True
            changed = True
        if layer.IsLocked:
            layer.IsLocked = False
            changed = True
        return changed

    _modify_layers(doc, _layer_indexes(doc, unlock_ids), _show_and_unlock)
    plan = _rename_export_layers(doc, export_ids)

    layer_from = Rhino.DocObjects.ObjectMaterialSource.MaterialFromLayer
    for obj_id in export_ids:
        obj = doc.Objects.FindId(obj_id)
        if obj is None:
            continue
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
    return plan


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

    try:
        restore_indexes = []
        for layer in doc.Layers:
            if layer is None or layer.IsDeleted:
                continue
            if layer.Id in layer_state:
                restore_indexes.append(int(layer.Index))

        def _restore_one(layer) -> bool:
            st = layer_state.get(layer.Id)
            if not st:
                return False
            layer.SetPersistentVisibility(bool(st[0]))
            layer.SetPersistentLocking(bool(st[1]))
            if len(st) > 2:
                layer.Name = st[2]
            return True

        _modify_layers(doc, restore_indexes, _restore_one)
    finally:
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
        _resume_autosave()


def _export_selected_usdz(export_ids, pending: Path, *, export_name: str) -> Result:
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

    last_err = None
    for attempt in (0, 1):
        cmd_path, copy_to = rhino_export_target(
            pending, export_name=export_name, attempt=attempt
        )
        try:
            cmd_path.encode("ascii")
        except UnicodeEncodeError:
            return Result.fail(
                "Export path is not ASCII: {}".format(cmd_path),
                stage="export_usdz",
            )
        if "(" in cmd_path or ")" in cmd_path:
            return Result.fail(
                "Export path still contains parentheses: {}".format(cmd_path),
                stage="export_usdz",
            )
        export_file = Path(cmd_path)
        if export_file.exists():
            try:
                export_file.unlink()
            except OSError:
                pass

        rs.UnselectAllObjects()
        selected = rs.SelectObjects(list(export_ids))
        try:
            selected_count = int(selected)
        except (TypeError, ValueError):
            selected_count = 0
        if selected_count != len(export_ids):
            return Result.fail(
                "Selected {} of {} object(s). Locked layers were not unlocked, so the USDZ was not published.".format(
                    selected_count, len(export_ids)
                ),
                stage="export_select",
            )
        quote = chr(34)
        cmd = "_-Export " + quote + cmd_path + quote + " _Enter _Enter"
        ok = rs.Command(cmd, False)
        wrote = export_file.is_file() and export_file.stat().st_size >= 32
        if not wrote:
            last_err = "USDZ was not created (command={}, path={}).".format(ok, cmd_path)
            continue

        try:
            shutil.copy2(str(export_file), str(copy_to))
        except OSError as exc:
            return Result.fail(
                "Could not copy TEMP USDZ to pending: {}".format(exc),
                stage="export_usdz",
            )
        try:
            export_file.unlink()
        except OSError:
            pass

        if pending.is_file() and pending.stat().st_size >= 32:
            return Result.success(stage="export_usdz", data=str(pending))
        last_err = "USDZ was not created. Check the path and Rhino USD export."

    return Result.fail(
        last_err or "USDZ was not created.",
        stage="export_usdz",
    )


def publish_models_once(
    *,
    layer: Optional[str] = None,
    include_kinds: Optional[Set[str]] = None,
    exclude_token: Optional[str] = None,
    interactive: bool = True,
) -> Result:
    """發布 `models/R2O.usdz`。取消／無物件不碰 last-good。"""
    import Rhino  # type: ignore
    import rhinoscriptsyntax as rs  # type: ignore

    target = _resolve_publish_target()
    if not target.ok:
        return target

    doc = Rhino.RhinoDoc.ActiveDoc
    if not doc:
        return Result.fail("No active document", stage="publish_models")

    sticky = _sticky()
    token = exclude_token
    if interactive and token is None:
        token = _prompt_exclude_token(
            sticky.get(_STICKY_EXCLUDE_TOKEN, DEFAULT_LAYER_EXCLUDE_TOKEN)
        )
        if token is None:
            return Result.blocked("Exclude token cancelled", stage="models_exclude")
    if token is None:
        token = DEFAULT_LAYER_EXCLUDE_TOKEN

    target_layer = layer
    if interactive and not target_layer:
        target_layer = _prompt_layer(doc, sticky.get(_STICKY_LAST_LAYER), token)
        if not target_layer:
            return Result.blocked("Layer selection cancelled", stage="models_layer")
    if not target_layer:
        return Result.blocked("No model layer specified", stage="models_layer")

    subtree = layer_subtree_paths(_all_layer_paths(doc), target_layer, exclude_token=token)
    if not subtree:
        return Result.blocked(
            "Layer '{}' was not found or is excluded".format(target_layer),
            stage="models_layer",
        )

    kinds_include = include_kinds
    kinds_labels: Optional[List[str]] = None
    if interactive and include_kinds is None:
        flags = _prompt_type_flags(doc, subtree, last_labels=sticky.get(_STICKY_LAST_TYPES))
        if not flags.ok:
            return flags
        kinds_include = flags.data["include"]
        kinds_labels = list(flags.data.get("labels") or [])
    if not kinds_include:
        kinds_include = set()
        for _lab, default, kinds in _TYPE_ROWS:
            if default:
                kinds_include.update(kinds)

    export_ids = _collect_export_ids(doc, subtree, kinds_include)
    if not export_ids:
        return Result.blocked(
            "No matching geometry in layer '{}'".format(target_layer),
            stage="models_collect",
        )

    root = target.data["root"]
    final = target.data["final"]
    pending = target.data["pending"]
    snap = None
    rs.EnableRedraw(False)
    try:
        snap = _capture_export_state(doc, export_ids)
        layer_materials = layer_material_names(doc, export_ids)
        plan = _prepare_export_visibility(doc, export_ids)
        exported = _export_selected_usdz(export_ids, pending, export_name=final.name)
        if not exported.ok:
            try:
                if pending.exists():
                    pending.unlink()
            except OSError:
                pass
            append_log(root, "Models publish: {} ({})".format(exported.status, exported.message))
            return exported

        promoted = promote_material_bindings_usdz(
            pending,
            payload_name=payload_name_for_final(final),
            layer_materials=layer_materials,
            path_alias=plan.get("path_alias"),
            layer_prim_names=plan.get("prim_names"),
        )
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
            sticky[_STICKY_EXCLUDE_TOKEN] = token
            if kinds_labels is not None:
                sticky[_STICKY_LAST_TYPES] = kinds_labels
            message = "Published {} object(s) from '{}' → {}".format(
                len(export_ids), target_layer, final
            )
            published = Result.success(message, stage=published.stage, data=str(final))
        append_log(
            root,
            "Models publish: {} ({}); layer={}; exclude={!r}; count={}".format(
                published.status, published.message, target_layer, token, len(export_ids)
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
