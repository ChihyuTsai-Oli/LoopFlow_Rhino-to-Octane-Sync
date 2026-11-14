# -*- coding: utf-8 -*-
"""Rhino Models 通道：R2B 同型三步視窗 → pending USDZ → 材質後處理 → atomic。"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from foundation.atomic import atomic_publish_from_pending
from foundation.export_cmd import (
    pack_usda_as_usdz,
    rhino_export_target,
    usda_inner_name,
    use_rhino9_runtime,
)
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
_USD_BLOCK_HANDLING = ("Embedded", "Ignore", "SeparateFiles")

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


def _prompt_exclude_token_rhino9(default_token: str) -> Optional[str]:
    """排除記號視窗固定在畫面中央。取消回 None，空白代表不排除。"""
    import Eto.Drawing as drawing  # type: ignore
    import Eto.Forms as forms  # type: ignore

    from rhino.ui.layer_picker import dialog_button_row, show_centered_dialog

    seed = default_token if default_token is not None else DEFAULT_LAYER_EXCLUDE_TOKEN

    class ExcludeDialog(forms.Dialog):
        def __init__(self):
            forms.Dialog.__init__(self)
            self.Title = "ROModels — Exclude Token"
            self.Padding = drawing.Padding(8)
            self.Resizable = False
            self.ClientSize = drawing.Size(420, 96)
            self.value = None

            label = forms.Label()
            label.Text = "Layer paths containing this text are skipped (blank = none)"
            box = forms.TextBox()
            box.Text = seed
            self._box = box

            ok = forms.Button()
            ok.Text = "OK"
            cancel = forms.Button()
            cancel.Text = "Cancel"
            ok.Click += self._on_ok
            cancel.Click += self._on_cancel
            self.DefaultButton = ok
            self.AbortButton = cancel

            layout = forms.DynamicLayout()
            layout.DefaultSpacing = drawing.Size(4, 6)
            layout.AddRow(label)
            layout.AddRow(box)
            layout.Add(dialog_button_row(ok, cancel), yscale=False)
            self.Content = layout

        def _on_ok(self, sender, e):
            self.value = str(self._box.Text or "")
            self.Close()

        def _on_cancel(self, sender, e):
            self.value = None
            self.Close()

    dialog = ExcludeDialog()
    show_centered_dialog(dialog)
    return dialog.value


def _prompt_exclude_token(default_token: str) -> Optional[str]:
    if use_rhino9_runtime(_rhino_major()):
        return _prompt_exclude_token_rhino9(default_token)

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


def checklist_flags(chosen) -> List[bool]:
    """勾選結果轉成旗標。rs 回 (文字, 勾選)；Rhino 9 直接回布林。"""
    flags: List[bool] = []
    for item in chosen:
        if isinstance(item, (tuple, list)):
            flags.append(bool(item[1]))
        else:
            flags.append(bool(item))
    return flags


def selected_type_labels(labels, flags, row_kinds):
    """勾選旗標對回類別標籤與 kind。沒勾回空集合。"""
    include: Set[str] = set()
    selected: List[str] = []
    for label, checked, kinds in zip(labels, flags, row_kinds):
        if checked:
            include.update(kinds)
            selected.append(label)
    return include, selected


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


def _show_type_checklist_rhino9(checklist: Sequence[Tuple[str, bool]]):
    """Rhino 9 用置中的勾選方塊。原生 CheckListBox 會閃退，也不會留在畫面中央。"""
    import Eto.Drawing as drawing  # type: ignore
    import Eto.Forms as forms  # type: ignore

    from rhino.ui.layer_picker import dialog_button_row, show_centered_dialog

    class TypeDialog(forms.Dialog):
        def __init__(self):
            forms.Dialog.__init__(self)
            self.Title = "ROModels"
            self.Padding = drawing.Padding(8)
            self.Resizable = False
            self.ClientSize = drawing.Size(420, 72 + 22 * max(1, len(checklist)))
            self.flags = None
            self._boxes = []

            label = forms.Label()
            label.Text = "Select geometry types to export"
            rows = forms.DynamicLayout()
            rows.DefaultSpacing = drawing.Size(4, 4)
            for text, checked in checklist:
                box = forms.CheckBox()
                box.Text = str(text)
                box.Checked = bool(checked)
                self._boxes.append(box)
                rows.AddRow(box)

            ok = forms.Button()
            ok.Text = "OK"
            cancel = forms.Button()
            cancel.Text = "Cancel"
            ok.Click += self._on_ok
            cancel.Click += self._on_cancel
            self.DefaultButton = ok
            self.AbortButton = cancel

            gap = forms.Label()
            gap.Text = ""
            rows.Add(gap, yscale=True)

            layout = forms.DynamicLayout()
            layout.DefaultSpacing = drawing.Size(4, 8)
            layout.AddRow(label)
            layout.Add(rows, yscale=True, xscale=True)
            layout.Add(dialog_button_row(ok, cancel), yscale=False)
            self.Content = layout

        def _on_ok(self, sender, e):
            self.flags = [bool(box.Checked) for box in self._boxes]
            self.Close()

        def _on_cancel(self, sender, e):
            self.flags = None
            self.Close()

    dialog = TypeDialog()
    show_centered_dialog(dialog)
    return dialog.flags


def _prompt_type_flags(doc, subtree: Sequence[str], last_labels: Optional[Sequence[str]] = None) -> Result:
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

    if use_rhino9_runtime(_rhino_major()):
        chosen = _show_type_checklist_rhino9(checklist)
    else:
        import rhinoscriptsyntax as rs  # type: ignore

        chosen = rs.CheckListBox(
            checklist,
            message="Select geometry types to export",
            title="ROModels",
        )
    if not chosen:
        return Result.blocked("Geometry type selection cancelled", stage="models_types")

    include, selected_labels = selected_type_labels(
        labels, checklist_flags(chosen), row_kinds
    )
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


def _layer_guid_key(value):
    if value is None:
        return None
    text = str(value).strip("{}").lower()
    if text == "00000000-0000-0000-0000-000000000000":
        return None
    return text


def layer_restore_assignment(own_visible, own_locked, parent_visible, parent_locked):
    """要不要寫回目前的 IsVisible／IsLocked。

    parent_* 為 None 表示沒有父層。回傳 None 表示不要賦值，
    避免子層把不可見的父層打開，或把鎖定的父層解鎖。
    """
    if not own_visible:
        set_visible = False
    elif parent_visible is False:
        set_visible = None
    else:
        set_visible = True

    if own_locked:
        set_locked = True
    elif parent_locked is True:
        set_locked = None
    else:
        set_locked = False
    return set_visible, set_locked


def plan_layer_restore(records):
    """父層在前。records 是 (key, parent_key, own_visible, own_locked)。

    回傳 [(key, set_visible, set_locked), ...]。set_* 為 None 表示不改目前狀態。
    """
    parent_of = {}
    own = {}
    for key, parent_key, visible, locked in records:
        parent_of[key] = parent_key
        own[key] = (bool(visible), bool(locked))

    depth = {}

    def depth_of(key, seen):
        if key in depth:
            return depth[key]
        if key in seen:
            depth[key] = 0
            return 0
        seen.add(key)
        parent_key = parent_of.get(key)
        if parent_key is None or parent_key not in parent_of:
            depth[key] = 0
        else:
            depth[key] = depth_of(parent_key, seen) + 1
        return depth[key]

    for key in parent_of:
        depth_of(key, set())
    ordered = sorted(parent_of, key=lambda key: (depth[key], str(key)))

    effective = {}
    planned = []
    for key in ordered:
        own_visible, own_locked = own[key]
        parent_key = parent_of.get(key)
        if parent_key in effective:
            parent_visible, parent_locked = effective[parent_key]
        else:
            parent_visible, parent_locked = None, None
        set_visible, set_locked = layer_restore_assignment(
            own_visible, own_locked, parent_visible, parent_locked
        )
        planned.append((key, set_visible, set_locked))
        effective[key] = (
            False if parent_visible is False else own_visible,
            True if parent_locked is True else own_locked,
        )
    return planned


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
        records = []
        index_of = {}
        for layer in doc.Layers:
            if layer is None or layer.IsDeleted or layer.Id not in layer_state:
                continue
            key = _layer_guid_key(layer.Id)
            parent_key = (
                None
                if _empty_layer_parent(layer)
                else _layer_guid_key(layer.ParentLayerId)
            )
            visible, locked = layer_state[layer.Id][0], layer_state[layer.Id][1]
            records.append((key, parent_key, visible, locked))
            index_of[key] = int(layer.Index)
        planned = plan_layer_restore(records)
        by_key = {key: (set_visible, set_locked) for key, set_visible, set_locked in planned}

        def _restore_one(layer) -> bool:
            st = layer_state.get(layer.Id)
            if not st:
                return False
            set_visible, set_locked = by_key.get(_layer_guid_key(layer.Id), (None, None))
            if set_visible is not None:
                layer.IsVisible = bool(set_visible)
            if set_locked is not None:
                layer.IsLocked = bool(set_locked)
            layer.SetPersistentVisibility(bool(st[0]))
            layer.SetPersistentLocking(bool(st[1]))
            if len(st) > 2:
                layer.Name = st[2]
            return True

        _modify_layers(
            doc,
            [index_of[key] for key, _set_visible, _set_locked in planned],
            _restore_one,
        )
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


def _rhino_major() -> int:
    try:
        import Rhino  # type: ignore

        return int(Rhino.RhinoApp.Version.Major)
    except Exception:
        return 0


def _prepare_export_path(cmd_path: str) -> Result:
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
    return Result.success(stage="export_usdz", data=cmd_path)


def _select_for_export(export_ids) -> Result:
    import rhinoscriptsyntax as rs  # type: ignore

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
    return Result.success(stage="export_select", data=selected_count)


def _clear_export_file(path: Path) -> None:
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def _copy_temp_usdz(export_file: Path, copy_to: Path, pending: Path) -> Optional[Result]:
    """複製成功且 pending 夠大才回成功。檔不夠大回 None，讓呼叫端換名重試。"""
    try:
        shutil.copy2(str(export_file), str(copy_to))
    except OSError as exc:
        return Result.fail(
            "Could not copy TEMP USDZ to pending: {}".format(exc),
            stage="export_usdz",
        )
    _clear_export_file(export_file)
    if pending.is_file() and pending.stat().st_size >= 32:
        return Result.success(stage="export_usdz", data=str(pending))
    return None


def _mesh_one_geometry(geom, Rhino):
    """把單一幾何做成新網格。曲線與點沒有網格。"""
    Mesh = Rhino.Geometry.Mesh
    if isinstance(geom, Mesh):
        return geom.DuplicateMesh()
    brep = geom if isinstance(geom, Rhino.Geometry.Brep) else None
    if brep is None:
        to_brep = getattr(geom, "ToBrep", None)
        if callable(to_brep):
            try:
                brep = to_brep()
            except Exception:
                brep = None
    if brep is None:
        return None
    pieces = Mesh.CreateFromBrep(brep, Rhino.Geometry.MeshingParameters.Default)
    if not pieces:
        return None
    if len(pieces) == 1:
        return pieces[0]
    joined = Mesh()
    for piece in pieces:
        joined.Append(piece)
    return joined


def _world_meshes_from_instance(doc, iref, Rhino, stack):
    """圖塊成員烤到世界座標。同一條鏈上的圖塊不再往下，避免循環。"""
    idef_id = iref.ParentIdefId
    if idef_id in stack:
        return []
    idef = doc.InstanceDefinitions.FindId(idef_id)
    if idef is None:
        return []
    chain = stack + (idef_id,)
    world = iref.Xform
    out = []
    for member in idef.GetObjects():
        geom = getattr(member, "Geometry", None)
        if geom is None:
            continue
        if isinstance(geom, Rhino.Geometry.InstanceReferenceGeometry):
            nested = geom.Duplicate()
            nested.Transform(world)
            out.extend(_world_meshes_from_instance(doc, nested, Rhino, chain))
            continue
        mesh = _mesh_one_geometry(geom, Rhino)
        if mesh is None:
            continue
        mesh.Transform(world)
        out.append(mesh)
    return out


def _bake_instances_for_export(doc, export_ids):
    """圖塊改成暫時的世界座標網格。回傳 (要匯出的 id, 結束後要刪的 id)。"""
    import Rhino  # type: ignore
    import System  # type: ignore

    keep = []
    temps = []
    instance_flag = Rhino.DocObjects.ObjectType.InstanceReference
    for oid in export_ids:
        obj = doc.Objects.FindId(oid)
        if obj is None or getattr(obj, "IsDeleted", False):
            continue
        geom = obj.Geometry
        if geom is None or not (obj.ObjectType & instance_flag):
            keep.append(oid)
            continue
        if not isinstance(geom, Rhino.Geometry.InstanceReferenceGeometry):
            keep.append(oid)
            continue
        meshes = _world_meshes_from_instance(doc, geom, Rhino, ())
        added = False
        try:
            attr = obj.Attributes.Duplicate()
        except Exception:
            attr = None
        for mesh in meshes:
            if mesh is None:
                continue
            try:
                new_id = doc.Objects.AddMesh(mesh, attr) if attr is not None else doc.Objects.AddMesh(mesh)
            except Exception:
                continue
            if new_id == System.Guid.Empty:
                continue
            temps.append(new_id)
            keep.append(new_id)
            added = True
        if not added:
            keep.append(oid)
    return keep, temps


def _delete_export_temps(doc, temps) -> None:
    for oid in temps:
        try:
            doc.Objects.Delete(oid, True)
        except Exception:
            pass


def usd_export_choice(default_layer, block_index, model_name, include_user_strings) -> dict:
    """Export USD 視窗的選擇。圖塊預設 Embedded，使用者字串預設開。"""
    try:
        index = int(block_index)
    except (TypeError, ValueError):
        index = 0
    if index < 0 or index >= len(_USD_BLOCK_HANDLING):
        index = 0
    return {
        "default_layer": str(default_layer or ""),
        "block_handling": _USD_BLOCK_HANDLING[index],
        "model_name": str(model_name or ""),
        "include_user_strings": bool(include_user_strings),
    }


def _prompt_export_usd_rhino9():
    """自己的 Export USD 視窗。取消回 None。不呼叫 Rhino 的命令列選項。"""
    import Eto.Drawing as drawing  # type: ignore
    import Eto.Forms as forms  # type: ignore
    from System.Collections.Generic import List as NetList  # type: ignore

    from rhino.ui.layer_picker import dialog_button_row, show_centered_dialog

    class ExportUsdDialog(forms.Dialog):
        def __init__(self):
            forms.Dialog.__init__(self)
            self.Title = "Export USD"
            self.Padding = drawing.Padding(8)
            self.Resizable = False
            self.ClientSize = drawing.Size(420, 280)
            self.value = None

            layer = forms.TextBox()
            self._layer = layer
            blocks = forms.DropDown()
            store = NetList[str]()
            store.Add("Embedded")
            store.Add("Ignore")
            store.Add("Separate files")
            blocks.DataStore = store
            blocks.SelectedIndex = 0
            self._blocks = blocks
            model = forms.TextBox()
            self._model = model
            users = forms.CheckBox()
            users.Text = "Include user strings"
            users.Checked = True
            self._users = users

            ok = forms.Button()
            ok.Text = "OK"
            cancel = forms.Button()
            cancel.Text = "Cancel"
            ok.Click += self._on_ok
            cancel.Click += self._on_cancel
            self.DefaultButton = ok
            self.AbortButton = cancel

            fields = forms.DynamicLayout()
            fields.DefaultSpacing = drawing.Size(4, 4)
            fields.AddRow(self._caption("Default layer"))
            fields.AddRow(layer)
            fields.AddRow(self._caption("Blocks"))
            fields.AddRow(blocks)
            fields.AddRow(self._caption("Model name"))
            fields.AddRow(model)
            fields.AddRow(users)
            gap = forms.Label()
            gap.Text = ""
            fields.Add(gap, yscale=True)

            layout = forms.DynamicLayout()
            layout.DefaultSpacing = drawing.Size(4, 6)
            layout.Add(fields, yscale=True, xscale=True)
            layout.Add(dialog_button_row(ok, cancel), yscale=False)
            self.Content = layout

        def _caption(self, text):
            import Eto.Forms as forms  # type: ignore

            label = forms.Label()
            label.Text = text
            return label

        def _on_ok(self, sender, e):
            try:
                index = int(self._blocks.SelectedIndex)
            except (TypeError, ValueError):
                index = 0
            self.value = usd_export_choice(
                self._layer.Text,
                index,
                self._model.Text,
                bool(self._users.Checked),
            )
            self.Close()

        def _on_cancel(self, sender, e):
            self.value = None
            self.Close()

    dialog = ExportUsdDialog()
    show_centered_dialog(dialog)
    return dialog.value


def _apply_usd_write_options(Rhino, chosen):
    """選項字典給 ExportSelected。網格一律打開，後處理只認網格。"""
    options = Rhino.FileIO.FileUsdWriteOptions()
    options.ForceMeshes = True
    if not chosen:
        options.IncludeUserStrings = False
        options.ModelName = ""
        options.BlockHandling = Rhino.FileIO.USDExportBlockHandling.Embedded
        return options
    options.IncludeUserStrings = bool(chosen.get("include_user_strings"))
    options.ModelName = str(chosen.get("model_name") or "")
    handling = str(chosen.get("block_handling") or "Embedded")
    table = {
        "Embedded": Rhino.FileIO.USDExportBlockHandling.Embedded,
        "Ignore": Rhino.FileIO.USDExportBlockHandling.Ignore,
        "SeparateFiles": Rhino.FileIO.USDExportBlockHandling.SeparateFiles,
    }
    options.BlockHandling = table.get(handling, table["Embedded"])
    if hasattr(options, "DefaultLayer"):
        options.DefaultLayer = str(chosen.get("default_layer") or "")
    return options


def _write_rhino9_usda(usda_path: Path, usd_options=None) -> Optional[str]:
    """Rhino 9 把目前選取寫成 ASCII USDA。失敗回錯誤字串。

    一律帶選項字典。不帶字典的 `ExportSelected` 只會在命令列問
    USD Export Options，取消也會用預設值直接寫檔。
    """
    import Rhino  # type: ignore

    doc = Rhino.RhinoDoc.ActiveDoc
    if doc is None:
        return "No active Rhino document"
    try:
        options = _apply_usd_write_options(Rhino, usd_options)
        wrote = bool(doc.ExportSelected(str(usda_path), options.ToDictionary()))
    except Exception as exc:
        return "Rhino 9 ExportSelected failed: {}".format(exc)
    if not wrote:
        return "Rhino 9 ExportSelected returned false ({})".format(usda_path)
    if not usda_path.is_file() or usda_path.stat().st_size < 32:
        return "USDA was not created ({})".format(usda_path)
    return None


def _export_selected_usdz_rhino9(
    export_ids, pending: Path, *, export_name: str, usd_options=None
) -> Result:
    import Rhino  # type: ignore

    doc = Rhino.RhinoDoc.ActiveDoc
    ids = list(export_ids)
    temps = []
    try:
        if doc is not None:
            ids, temps = _bake_instances_for_export(doc, ids)
        return _export_selected_usdz_rhino9_ids(
            ids,
            pending,
            export_name=export_name,
            usd_options=usd_options,
        )
    finally:
        if doc is not None and temps:
            _delete_export_temps(doc, temps)


def _export_selected_usdz_rhino9_ids(
    export_ids, pending: Path, *, export_name: str, usd_options
) -> Result:
    inner = usda_inner_name(export_name, pending)
    last_err = None
    for attempt in (0, 1):
        cmd_path, copy_to = rhino_export_target(
            pending, export_name=export_name, attempt=attempt
        )
        ready = _prepare_export_path(cmd_path)
        if not ready.ok:
            return ready
        usdz_file = Path(cmd_path)
        usda_file = usdz_file.with_suffix(".usda")
        _clear_export_file(usdz_file)
        _clear_export_file(usda_file)
        selected = _select_for_export(export_ids)
        if not selected.ok:
            return selected
        err = _write_rhino9_usda(usda_file, usd_options)
        if err:
            last_err = err
            continue
        try:
            pack_usda_as_usdz(usda_file, usdz_file, inner)
        except OSError as exc:
            last_err = "Could not pack USDA into USDZ: {}".format(exc)
            continue
        _clear_export_file(usda_file)
        copied = _copy_temp_usdz(usdz_file, copy_to, pending)
        if copied is None:
            last_err = "USDZ was not created. Check the path and Rhino USD export."
            continue
        return copied
    return Result.fail(
        last_err or "USDZ was not created.",
        stage="export_usdz",
    )


def _export_selected_usdz_command(export_ids, pending: Path, *, export_name: str) -> Result:
    """Rhino 8：`_-Export` 寫 TEMP USDZ。"""
    import rhinoscriptsyntax as rs  # type: ignore

    last_err = None
    for attempt in (0, 1):
        cmd_path, copy_to = rhino_export_target(
            pending, export_name=export_name, attempt=attempt
        )
        ready = _prepare_export_path(cmd_path)
        if not ready.ok:
            return ready
        export_file = Path(cmd_path)
        _clear_export_file(export_file)
        selected = _select_for_export(export_ids)
        if not selected.ok:
            return selected
        quote = chr(34)
        cmd = "_-Export " + quote + cmd_path + quote + " _Enter _Enter"
        ok = rs.Command(cmd, False)
        wrote = export_file.is_file() and export_file.stat().st_size >= 32
        if not wrote:
            last_err = "USDZ was not created (command={}, path={}).".format(ok, cmd_path)
            continue
        copied = _copy_temp_usdz(export_file, copy_to, pending)
        if copied is None:
            last_err = "USDZ was not created. Check the path and Rhino USD export."
            continue
        return copied
    return Result.fail(
        last_err or "USDZ was not created.",
        stage="export_usdz",
    )


def _export_selected_usdz(
    export_ids, pending: Path, *, export_name: str, usd_options=None
) -> Result:
    pending.parent.mkdir(parents=True, exist_ok=True)
    if pending.exists():
        try:
            pending.unlink()
        except OSError as exc:
            return Result.fail(
                "Cannot clear pending USDZ: {}".format(exc),
                stage="export_usdz",
            )
    if use_rhino9_runtime(_rhino_major()):
        return _export_selected_usdz_rhino9(
            export_ids,
            pending,
            export_name=export_name,
            usd_options=usd_options,
        )
    return _export_selected_usdz_command(
        export_ids, pending, export_name=export_name
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

    payload = {
        "doc": doc,
        "export_ids": export_ids,
        "root": target.data["root"],
        "final": target.data["final"],
        "pending": target.data["pending"],
        "document": target.data["document"],
        "target_layer": target_layer,
        "token": token,
        "kinds_labels": kinds_labels,
        "sticky": sticky,
    }
    # 不帶選項的 ExportSelected 只會在命令列問 USD Export Options，取消也會直接寫檔。
    if interactive and use_rhino9_runtime(_rhino_major()):
        chosen = _prompt_export_usd_rhino9()
        if chosen is None:
            return Result.cancel("Export USD cancelled", stage="export_usdz")
        payload["usd_options"] = chosen
    return _run_models_publish(payload)


def _run_models_publish(payload) -> Result:
    """寫 USD、後處理、發布，並在結束時還原文件。"""
    import rhinoscriptsyntax as rs  # type: ignore

    doc = payload["doc"]
    export_ids = payload["export_ids"]
    root = payload["root"]
    final = payload["final"]
    pending = payload["pending"]
    target_layer = payload["target_layer"]
    token = payload["token"]
    kinds_labels = payload["kinds_labels"]
    sticky = payload["sticky"]
    snap = None
    rs.EnableRedraw(False)
    try:
        snap = _capture_export_state(doc, export_ids)
        layer_materials = layer_material_names(doc, export_ids)
        plan = _prepare_export_visibility(doc, export_ids)
        exported = _export_selected_usdz(
            export_ids,
            pending,
            export_name=final.name,
            usd_options=payload.get("usd_options"),
        )
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
            write_current_project_pointer(root, payload["document"])
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
