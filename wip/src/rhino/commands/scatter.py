# -*- coding: utf-8 -*-
"""Rhino Scatter 通道：選 Block → 原點匯出 USD → atomic；來源一律還原。"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional

from foundation.atomic import atomic_publish_from_pending
from foundation.export_cmd import rhino_export_target
from foundation.log import append_log
from foundation.paths import (
    config_root_for_document,
    ensure_config_layout,
    pending_path_for,
    require_saved_document_path,
    scatter_path,
)
from foundation.pointer import write_current_project_pointer
from foundation.result import Result
from foundation.scatter_names import map_block_stems


def _resolve_root() -> Result:
    import scriptcontext as sc  # type: ignore

    doc = sc.doc
    path = getattr(doc, "Path", None) if doc else None
    saved = require_saved_document_path(path)
    if not saved.ok:
        return saved
    root = ensure_config_layout(config_root_for_document(saved.data))
    return Result.success(
        data={"root": root, "document": saved.data},
        stage="resolve_path",
    )


def _validate_usd_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return "USD is missing"
    if path.stat().st_size < 32:
        return "USD is too small"
    return None


def _export_selected_usd(oid, pending: Path) -> Result:
    import rhinoscriptsyntax as rs  # type: ignore

    pending.parent.mkdir(parents=True, exist_ok=True)
    if pending.exists():
        try:
            pending.unlink()
        except OSError as exc:
            return Result.fail(
                "Cannot clear pending USD: {}".format(exc),
                stage="export_usd",
            )

    cmd_path, copy_to = rhino_export_target(pending)
    try:
        cmd_path.encode("ascii")
    except UnicodeEncodeError:
        return Result.fail(
            "Export path is not ASCII: {}".format(cmd_path),
            stage="export_usd",
        )
    if "(" in cmd_path or ")" in cmd_path:
        return Result.fail(
            "Export path still contains parentheses: {}".format(cmd_path),
            stage="export_usd",
        )
    export_file = Path(cmd_path)
    if export_file.exists() and copy_to is not None:
        try:
            export_file.unlink()
        except OSError:
            pass

    rs.UnselectAllObjects()
    rs.SelectObject(oid)
    quote = chr(34)
    cmd = "_-Export " + quote + cmd_path + quote + " _Enter _Enter"
    ok = rs.Command(cmd, False)
    wrote = export_file.is_file() and export_file.stat().st_size >= 32
    if not wrote:
        return Result.fail(
            "USD was not created (command={}, path={}).".format(ok, cmd_path),
            stage="export_usd",
        )

    if copy_to is not None:
        try:
            shutil.copy2(str(export_file), str(copy_to))
        except OSError as exc:
            return Result.fail(
                "Could not copy TEMP USD to pending: {}".format(exc),
                stage="export_usd",
            )
        try:
            export_file.unlink()
        except OSError:
            pass

    if not pending.is_file() or pending.stat().st_size < 32:
        return Result.fail(
            "USD was not created. Check the path and Rhino USD export.",
            stage="export_usd",
        )
    return Result.success(stage="export_usd", data=str(pending))


def publish_scatter_once(*, interactive: bool = True) -> Result:
    """
    把選取 Block 各匯一份 `scatter/<Block名>.usd`。

    單項失敗繼續；來源位移必須還原。取消／非 Block 不發布。
    """
    import rhinoscriptsyntax as rs  # type: ignore

    target = _resolve_root()
    if not target.ok:
        return target
    root = target.data["root"]

    obj_ids = rs.GetObjects(
        "Select Block objects to export",
        filter=0,
        preselect=True,
        select=False,
    )
    if not obj_ids:
        return Result.cancel("No objects selected", stage="scatter_select")

    non_blocks = [oid for oid in obj_ids if not rs.IsBlockInstance(oid)]
    if non_blocks:
        return Result.blocked(
            "The selection contains {} non-Block object(s). Select Blocks only.".format(
                len(non_blocks)
            ),
            stage="scatter_select",
        )

    unique: Dict[str, object] = {}
    for oid in obj_ids:
        name = rs.BlockInstanceName(oid)
        if name and name not in unique:
            unique[name] = oid
    if not unique:
        return Result.blocked("Could not read Block definition names", stage="scatter_select")

    mapped = map_block_stems(list(unique.keys()))
    if not mapped.ok:
        append_log(root, "Scatter publish: {} ({})".format(mapped.status, mapped.message))
        return mapped
    stem_to_source: Dict[str, str] = mapped.data

    previous_selection = list(rs.SelectedObjects() or [])
    import scriptcontext as sc  # type: ignore

    doc = sc.doc
    previous_modified = bool(getattr(doc, "Modified", False)) if doc else False

    exported: List[str] = []
    failed: List[str] = []
    rs.EnableRedraw(False)
    try:
        for stem, block_name in stem_to_source.items():
            oid = unique[block_name]
            ins_pt = rs.BlockInstanceInsertPoint(oid)
            if ins_pt is None:
                failed.append("{} (no insertion point)".format(block_name))
                continue
            move_to_origin = [-ins_pt.X, -ins_pt.Y, -ins_pt.Z]
            move_back = [ins_pt.X, ins_pt.Y, ins_pt.Z]
            moved = False
            final = scatter_path(root, stem)
            pending = pending_path_for(final)
            try:
                if not rs.MoveObject(oid, move_to_origin):
                    failed.append("{} (could not move to origin)".format(block_name))
                    continue
                moved = True
                exported_one = _export_selected_usd(oid, pending)
                if not exported_one.ok:
                    try:
                        if pending.exists():
                            pending.unlink()
                    except OSError:
                        pass
                    failed.append("{} ({})".format(block_name, exported_one.message))
                    continue
                published = atomic_publish_from_pending(
                    final, pending_path=pending, validate=_validate_usd_file
                )
                if published.ok:
                    exported.append(str(final))
                else:
                    failed.append("{} ({})".format(block_name, published.message))
            except Exception as exc:
                try:
                    if pending.exists():
                        pending.unlink()
                except OSError:
                    pass
                failed.append("{} ({})".format(block_name, exc))
            finally:
                if moved:
                    try:
                        restored = rs.MoveObject(oid, move_back)
                    except Exception as restore_exc:
                        restored = False
                        restore_exc_msg = str(restore_exc)
                    else:
                        restore_exc_msg = ""
                    if not restored:
                        detail = restore_exc_msg or "MoveObject returned false"
                        fail = Result.fail(
                            "Could not restore Block '{}': {}".format(
                                block_name, detail
                            ),
                            stage="scatter_restore",
                        )
                        append_log(
                            root,
                            "Scatter publish: {} ({})".format(fail.status, fail.message),
                        )
                        return fail
    finally:
        try:
            rs.UnselectAllObjects()
            if previous_selection:
                rs.SelectObjects(previous_selection)
        except Exception:
            pass
        try:
            if doc is not None:
                doc.Modified = previous_modified
        except Exception:
            pass
        rs.EnableRedraw(True)

    if exported:
        write_current_project_pointer(root, target.data["document"])

    if not exported and failed:
        result = Result.fail(
            "No Scatter USD published. Failed: {}".format("; ".join(failed)),
            stage="publish_scatter",
        )
    elif failed:
        result = Result.success(
            "Published {} file(s); failed: {}".format(len(exported), "; ".join(failed)),
            stage="publish_scatter",
            data=exported,
        )
    else:
        result = Result.success(
            "Published {} Scatter USD file(s)".format(len(exported)),
            stage="publish_scatter",
            data=exported,
        )
    append_log(
        root,
        "Scatter publish: {} ({}); ok={}; fail={}".format(
            result.status, result.message, len(exported), len(failed)
        ),
    )
    return result
