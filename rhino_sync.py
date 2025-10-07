import scriptcontext as sc


def write_usertext_ui(obj_id, key, val):
    """Thread-safe write of a single UserText key to a Rhino object.

    - Executes on Rhino UI thread when possible
    - Wraps change in an Undo record
    - Triggers a Views.Redraw()
    """
    try:
        import Rhino
        import System
        ok_ref = {"ok": False}

        def _do():
            try:
                ro = sc.doc.Objects.FindId(obj_id)
            except Exception:
                ro = None
            if ro is None:
                ok_ref["ok"] = False; return
            try:
                if getattr(ro, 'IsLocked', False):
                    ok_ref["ok"] = False; return
            except Exception:
                pass
            attrs = None
            try:
                attrs = ro.Attributes.Duplicate()
            except Exception:
                attrs = None
            if attrs is None:
                ok_ref["ok"] = False; return
            try:
                attrs.SetUserString(key, "" if val is None else str(val))
            except Exception:
                ok_ref["ok"] = False; return
            rec = None
            try:
                rec = sc.doc.BeginUndoRecord("UserText Edit")
            except Exception:
                rec = None
            try:
                ok2 = sc.doc.Objects.ModifyAttributes(ro, attrs, True)
            except Exception:
                ok2 = False
            try:
                if rec is not None:
                    sc.doc.EndUndoRecord(rec)
            except Exception:
                pass
            try:
                sc.doc.Views.Redraw()
            except Exception:
                pass
            ok_ref["ok"] = bool(ok2)

        try:
            Rhino.RhinoApp.InvokeOnUiThread(System.Action(_do))
        except Exception:
            _do()
        return ok_ref.get("ok", False)
    except Exception:
        return False


