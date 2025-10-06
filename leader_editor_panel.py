import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import Rhino.UI
import os
import json


def _load_config_local():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        script_dir = os.getcwd()
    default = {
        "export": {
            "na_value": "NA",
            "floor_sort": True
        }
    }
    try:
        cfg_path = os.path.join(script_dir, "config.json")
        if os.path.isfile(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                default[k] = v
    except Exception:
        pass
    return default


def _scan_leaders_for_editor(cfg):
    leaders = []
    keys_union = []
    seen_keys = set()
    try:
        for obj in sc.doc.Objects:
            try:
                geom = obj.Geometry
            except Exception:
                continue
            if isinstance(geom, Rhino.Geometry.Leader):
                leader = geom
                dimstyle_id = leader.DimensionStyleId
                dimstyle = sc.doc.DimStyles.FindId(dimstyle_id)
                text = leader.Text.replace('\r\n', ' ').replace('\n', ' ')
                udict = {}
                keys = obj.Attributes.GetUserStrings()
                if keys:
                    for k in keys.AllKeys:
                        try:
                            v = keys[k]
                        except Exception:
                            v = None
                        if k not in udict:
                            udict[k] = v
                        if k not in seen_keys:
                            seen_keys.add(k)
                            keys_union.append(k)
                # ensure LeaderGUID
                try:
                    guid_text = str(obj.Id)
                except Exception:
                    guid_text = None
                if udict.get("LeaderGUID") is None and guid_text:
                    udict["LeaderGUID"] = guid_text
                    if "LeaderGUID" not in seen_keys:
                        seen_keys.add("LeaderGUID")
                        keys_union.append("LeaderGUID")
                leaders.append({
                    "text": text,
                    "dimstyle": dimstyle.Name if dimstyle else "",
                    "guid": guid_text,
                    "user": udict,
                })
    except Exception:
        pass
    return leaders, keys_union


def show_leader_editor():
    try:
        import Eto.Forms as forms
        import Eto.Drawing as drawing
    except Exception as ex:
        print("[LeaderEditor] Eto not available:", ex)
        return

    cfg = _load_config_local()
    try:
        active_doc = Rhino.RhinoDoc.ActiveDoc
        if active_doc is not None:
            sc.doc = active_doc
    except Exception:
        pass

    leaders, keys_union = _scan_leaders_for_editor(cfg)
    if not leaders:
        print("[LeaderEditor] No leaders found.")
    # Build grid data
    header_keys = ["text", "dimstyle"] + [k for k in keys_union if k != "LeaderGUID"] + ["LeaderGUID"]

    form = forms.Form()
    form.Title = "Leader Editor (Modeless)"
    try:
        form.ClientSize = drawing.Size(1000, 640)
    except Exception:
        pass

    layout = forms.DynamicLayout()
    layout.Padding = drawing.Padding(10)
    layout.Spacing = drawing.Size(6, 6)

    search_tb = forms.TextBox()
    try:
        search_tb.PlaceholderText = "Search"
    except Exception:
        pass
    layout.AddRow(search_tb)

    grid = forms.TreeGridView()
    grid.ShowHeader = True
    grid.AllowMultipleSelection = False
    try:
        grid.RowHeight = 22
    except Exception:
        pass

    # Column setup
    col_keys = list(header_keys)
    def add_col(idx, name, width=None, editable=False, visible=True):
        col = forms.GridColumn()
        col.HeaderText = name
        try:
            if width:
                col.Width = width
        except Exception:
            pass
        try:
            col.Editable = editable
        except Exception:
            pass
        try:
            col.Sortable = True
        except Exception:
            pass
        col.DataCell = forms.TextBoxCell(idx)
        try:
            col.Visible = bool(visible)
        except Exception:
            if not visible:
                try:
                    col.Width = 0
                except Exception:
                    pass
        grid.Columns.Add(col)
        return col

    add_col(0, "text", 260, editable=False)
    add_col(1, "dimstyle", 180, editable=False)
    # editable keys in-between
    for i, k in enumerate(header_keys[2:-1]):
        add_col(i + 2, k, editable=True)
    # hidden GUID
    add_col(len(header_keys) - 1, "LeaderGUID", editable=False, visible=False)

    # Build initial store
    def build_rows(source):
        try:
            items = forms.TreeGridItemCollection()
        except Exception:
            class _S(list):
                pass
            items = _S()
        for it in source:
            vals = []
            vals.append(it.get("text", ""))
            vals.append(it.get("dimstyle", ""))
            user = it.get("user") or {}
            for k in header_keys[2:-1]:
                vals.append("" if user.get(k) is None else str(user.get(k)))
            vals.append(it.get("guid", ""))
            try:
                tri = forms.TreeGridItem(vals)
            except Exception:
                tri = forms.TreeGridItem()
                tri.Values = vals
            try:
                items.Add(tri)
            except Exception:
                items.append(tri)
        return items

    state = {"rows": leaders, "view": leaders}
    grid.DataStore = build_rows(state["view"])

    def apply_filter():
        s = (search_tb.Text or "").strip().lower()
        if not s:
            state["view"] = list(state["rows"])
        else:
            filtered = []
            for it in state["rows"]:
                try:
                    joined = "{} {} {}".format(it.get("text", ""), it.get("dimstyle", ""), " ".join(["{}={}".format(k, v) for k, v in (it.get("user") or {}).items() if v is not None])).lower()
                    if s in joined:
                        filtered.append(it)
                except Exception:
                    pass
            state["view"] = filtered
        grid.DataStore = build_rows(state["view"])

    search_tb.TextChanged += lambda s, e: apply_filter()

    # Commit on cell edited (RhinoCommon)
    def on_cell_edited(sender, e):
        try:
            col_index = -1
            try:
                for i in range(len(grid.Columns)):
                    if grid.Columns[i] == e.Column:
                        col_index = i; break
            except Exception:
                col_index = -1
            if col_index < 0 or col_index >= len(col_keys):
                return
            key = col_keys[col_index]
            if key in ("text", "dimstyle", "LeaderGUID"):
                return
            vals = None
            try:
                vals = e.Item.Values
            except Exception:
                vals = None
            if vals is None:
                return
            new_val = vals[col_index] if col_index < len(vals) else ""
            guid_text = None
            try:
                gidx = col_keys.index("LeaderGUID")
                if gidx < len(vals):
                    guid_text = vals[gidx]
            except Exception:
                guid_text = None
            if not guid_text:
                return
            import System
            try:
                obj_id = System.Guid(guid_text)
            except Exception:
                obj_id = None
            if obj_id is None:
                return
            # Write via RhinoCommon
            ro = sc.doc.Objects.FindId(obj_id)
            if ro is None:
                return
            try:
                if ro.IsLocked:
                    return
            except Exception:
                pass
            attrs = None
            try:
                attrs = ro.Attributes.Duplicate()
            except Exception:
                attrs = None
            if attrs is None:
                return
            try:
                attrs.SetUserString(key, "" if new_val is None else str(new_val))
            except Exception:
                return
            ok = False
            try:
                rec = sc.doc.BeginUndoRecord("Leader Editor Edit")
            except Exception:
                rec = None
            try:
                ok = sc.doc.Objects.ModifyAttributes(ro, attrs, True)
            except Exception:
                ok = False
            try:
                if rec is not None:
                    sc.doc.EndUndoRecord(rec)
            except Exception:
                pass
            if ok:
                try:
                    sc.doc.Views.Redraw()
                except Exception:
                    pass
                # update cached row model
                try:
                    for it in state["rows"]:
                        if it.get("guid") == guid_text:
                            it.get("user", {})[key] = "" if new_val is None else str(new_val)
                            break
                except Exception:
                    pass
        except Exception:
            pass

    try:
        grid.CellEdited += on_cell_edited
    except Exception:
        pass

    # Buttons
    def on_refresh(sender, e):
        try:
            leaders2, keys2 = _scan_leaders_for_editor(cfg)
        except Exception:
            leaders2, keys2 = [], []
        # Rebuild columns if key set changed is more complex; for now just rebuild rows
        state["rows"] = leaders2
        state["view"] = leaders2
        apply_filter()

    def on_show(sender, e):
        try:
            sel = grid.SelectedItem
        except Exception:
            sel = None
        if sel is None:
            return
        vals = None
        try:
            vals = sel.Values
        except Exception:
            vals = None
        if not vals:
            return
        guid_text = None
        try:
            gidx = col_keys.index("LeaderGUID")
            if gidx < len(vals):
                guid_text = vals[gidx]
        except Exception:
            guid_text = None
        if not guid_text:
            return
        try:
            import System
            obj_id = System.Guid(guid_text)
        except Exception:
            obj_id = None
        if obj_id:
            try:
                rs.UnselectAllObjects()
            except Exception:
                pass
            try:
                rs.SelectObject(obj_id)
                rs.ZoomSelected()
            except Exception:
                pass

    btn_refresh = forms.Button()
    btn_show = forms.Button()
    btn_close = forms.Button()
    try:
        btn_refresh.Text = "Refresh"
        btn_show.Text = "Show"
        btn_close.Text = "Close"
    except Exception:
        pass
    try:
        btn_refresh.Click += on_refresh
        btn_show.Click += on_show
        btn_close.Click += lambda s, e: form.Close()
    except Exception:
        pass

    layout.AddRow(grid)
    layout.AddSeparateRow(None, btn_show, btn_refresh, btn_close)
    form.Content = layout

    try:
        form.Show()
    except Exception:
        try:
            Rhino.UI.EtoExtensions.ShowSemiModal(form, sc.doc, Rhino.UI.RhinoEtoApp.MainWindow)
        except Exception:
            form.Show()



