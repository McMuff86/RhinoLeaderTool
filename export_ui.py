# UI helpers for export dialog and preview
# Note: kept minimal; main logic still resides in write_leaders_to_file.py

def group_radio_buttons(forms, drawing):
    rb_desktop = forms.RadioButton(); rb_desktop.Text = "Desktop (Standardpfad)"; rb_desktop.Checked = True
    try:
        rb_doc = forms.RadioButton(rb_desktop)
    except Exception:
        rb_doc = forms.RadioButton()
        try:
            rb_doc.Group = rb_desktop
        except Exception:
            pass
    rb_doc.Text = "Ordner der 3dm-Datei"
    return rb_desktop, rb_doc

def show_preview_dialog(cfg, leaders, final_keys):
    try:
        import rhinoscriptsyntax as rs
        import scriptcontext as sc
        import Rhino
        import Eto.Forms as forms
        import Eto.Drawing as drawing
        from rhino_sync import write_usertext_ui as _write_usertext_ui
    except Exception as e:
        try:
            print("[Preview] UI not available:", e)
        except Exception:
            pass
        return True

    try:
        # Debug helper: write to Rhino StatusBar and console/print as fallback
        def _dbg(*parts):
            msg = " ".join([str(p) for p in parts])
            try:
                Rhino.UI.StatusBar.SetText(msg)
            except Exception:
                pass
            try:
                Rhino.RhinoApp.WriteLine(msg)
            except Exception:
                try:
                    print(msg)
                except Exception:
                    pass

        dialog = forms.Dialog()
        dialog.Title = "Vorschau – Export"
        layout = forms.DynamicLayout()
        layout.Spacing = drawing.Size(6, 6)
        layout.Padding = drawing.Padding(10)
        try:
            dialog.ClientSize = drawing.Size(980, 600)
        except Exception:
            pass
        try:
            dialog.Resizable = True
        except Exception:
            pass

        header_cols = ["text", "dimstyle"] + list(final_keys)
        # Daten vorbereiten (Liste von Dicts)
        rows = []
        guid_to_row = {}
        guid_to_leader = {}
        pending_changes = {}
        def add_pending(guid_text, key, value):
            try:
                if not guid_text or key in ("text", "dimstyle", "LeaderGUID"):
                    return
                if guid_text not in pending_changes:
                    pending_changes[guid_text] = {}
                pending_changes[guid_text][key] = "" if value is None else str(value)
                try:
                    if pending_count_lbl is not None:
                        total = sum(len(v) for v in pending_changes.values())
                        pending_count_lbl.Text = "Änderungen: {}".format(total)
                except Exception:
                    pass
            except Exception:
                pass
        try:
            for it in leaders:
                try:
                    gtxt = None
                    try:
                        gtxt = it.get("user", {}).get("LeaderGUID")
                    except Exception:
                        gtxt = None
                    if gtxt:
                        guid_to_leader[str(gtxt)] = it
                except Exception:
                    pass
        except Exception:
            pass
        for item in leaders:
            r = {"text": item.get("text", ""), "dimstyle": item.get("dimstyle", "")}
            user = item.get("user") or {}
            for k in final_keys:
                try:
                    r[k] = "" if k not in user else ("" if user.get(k) is None else str(user.get(k)))
                except Exception:
                    r[k] = ""
            try:
                guid_val = user.get("LeaderGUID")
            except Exception:
                guid_val = None
            # persist guid under two keys: visible map key and internal helper
            if guid_val is not None:
                r["LeaderGUID"] = str(guid_val)
            r["_guid"] = None if guid_val is None else str(guid_val)
            rows.append(r)
            if r.get("_guid"):
                guid_to_row[r.get("_guid")] = r

        # Content-Bereich mit Scrollbar, Buttons bleiben unten fix
        content_panel = forms.DynamicLayout(); content_panel.Spacing = drawing.Size(6, 6)
        # Suchfeld (wirkt auf beide Ansichten) – direkt neben dem Label platzieren
        search_lbl = forms.Label(); search_lbl.Text = "Suche:"
        search_tb = forms.TextBox()
        try:
            search_tb.Size = drawing.Size(320, -1)
        except Exception:
            pass
        # separate row mit trailing None hält Feld direkt neben Label links
        try:
            content_panel.AddSeparateRow(search_lbl, search_tb, None)
        except Exception:
            content_panel.AddRow(search_lbl, search_tb)

        tabs = forms.TabControl()
        content_panel.AddRow(tabs)

        # 1) Listenansicht
        try:
            list_page = forms.TabPage(); list_page.Text = "Liste"
            listbox = forms.ListBox()
            compact_rows = []
            for item in rows:
                try:
                    pairs = []
                    for k in final_keys:
                        v = item.get(k, "")
                        if v is None or str(v).strip() == "":
                            continue
                        pairs.append("{}={}".format(k, v))
                    compact = "{} | {}{}".format(item.get("text", ""), item.get("dimstyle", ""), (" | "+" | ".join(pairs)) if pairs else "")
                except Exception:
                    compact = str(item)
                compact_rows.append(compact)
            listbox.DataStore = compact_rows
            def apply_filter_list():
                try:
                    s = (search_tb.Text or "").strip().lower()
                    if not s:
                        listbox.DataStore = compact_rows
                        return
                    filtered = [r for r in compact_rows if s in r.lower()]
                    listbox.DataStore = filtered
                except Exception:
                    listbox.DataStore = compact_rows
            search_tb.TextChanged += lambda s, e: apply_filter_list()
            apply_filter_list()
            try:
                list_scroll = forms.Scrollable(); list_scroll.Content = listbox
                try:
                    list_scroll.ExpandContentWidth = True
                    list_scroll.ExpandContentHeight = False
                except Exception:
                    pass
                list_page.Content = list_scroll
            except Exception:
                list_page.Content = listbox
            tabs.Pages.Add(list_page)
        except Exception:
            pass

        # 2) Tabellenansicht
        grid = None
        try:
            grid_page = forms.TabPage(); grid_page.Text = "Tabelle"
            grid = forms.TreeGridView()
            grid.ShowHeader = True
            grid.AllowMultipleSelection = False
            grid.Height = 420
            try:
                grid.RowHeight = 22
            except Exception:
                pass
            row_data = list(rows)
            row_view_ref = {"data": row_data}
            col_keys = ["text", "dimstyle"]
            def add_col(idx, name, width=None):
                col = forms.GridColumn(); col.HeaderText = name
                try:
                    if width:
                        col.Width = width
                except Exception:
                    pass
                try:
                    col.Editable = (name not in ("text", "dimstyle", "LeaderGUID"))
                except Exception:
                    pass
                try:
                    col.Sortable = True
                except Exception:
                    pass
                col.DataCell = forms.TextBoxCell(idx)
                grid.Columns.Add(col)
                return col
            add_col(0, "text", 260)
            add_col(1, "dimstyle", 180)
            max_cols = 40
            for i, k in enumerate(final_keys):
                if i >= max_cols:
                    break
                add_col(i + 2, k)
                col_keys.append(k)
            if "LeaderGUID" not in col_keys:
                col_keys.append("LeaderGUID")
                try:
                    _guid_col = add_col(len(col_keys) - 1, "LeaderGUID")
                    try:
                        _guid_col.Visible = False
                    except Exception:
                        try:
                            _guid_col.Width = 0
                        except Exception:
                            pass
                except Exception:
                    pass

            def build_store(data_rows):
                try:
                    items = forms.TreeGridItemCollection()
                except Exception:
                    items = None
                if items is None:
                    class _SimpleStore(list): pass
                    items = _SimpleStore()
                for r in data_rows:
                    try:
                        vals = ["" if r.get(k) is None else str(r.get(k)) for k in col_keys]
                    except Exception:
                        vals = ["" for _ in col_keys]
                    try:
                        it = forms.TreeGridItem(vals)
                    except Exception:
                        it = forms.TreeGridItem(); it.Values = vals
                    try:
                        items.Add(it)
                    except Exception:
                        items.append(it)
                return items

            sort_state = {"key": None, "desc": False}
            def on_header_click(sender, e):
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
                    if sort_state.get("key") == key:
                        sort_state["desc"] = not bool(sort_state.get("desc", False))
                    else:
                        sort_state["key"] = key; sort_state["desc"] = False
                    data = list(row_view_ref.get("data") or [])
                    def make_sort_tuple(val):
                        try:
                            if val is None:
                                return (2, "")
                            s = str(val).strip()
                            try:
                                return (0, float(s.replace(",", ".")))
                            except Exception:
                                return (1, s.lower())
                        except Exception:
                            return (2, "")
                    try:
                        data.sort(key=lambda r: make_sort_tuple(r.get(key)), reverse=bool(sort_state["desc"]))
                    except Exception:
                        pass
                    row_view_ref["data"] = data
                    grid.DataStore = build_store(data)
                except Exception:
                    pass
            wired = False
            try:
                grid.ColumnHeaderClick += on_header_click; wired = True
            except Exception:
                wired = False
            if not wired:
                try:
                    for c in grid.Columns:
                        try:
                            c.HeaderClick += on_header_click; wired = True
                        except Exception:
                            pass
                except Exception:
                    pass

            def update_change_counter():
                try:
                    try:
                        guid_idx = col_keys.index("LeaderGUID")
                    except Exception:
                        guid_idx = -1
                    if guid_idx < 0:
                        return
                    try:
                        datastore = grid.DataStore
                    except Exception:
                        datastore = None
                    if datastore is None:
                        return
                    changes = 0
                    for item in datastore:
                        try:
                            vals = item.Values
                        except Exception:
                            vals = None
                        if vals is None or guid_idx >= len(vals):
                            continue
                        guid_text = vals[guid_idx]
                        if not guid_text:
                            try:
                                t_idx = col_keys.index("text")
                            except Exception:
                                t_idx = -1
                            if t_idx >= 0 and t_idx < len(vals):
                                row_txt = vals[t_idx]
                                if row_txt:
                                    try:
                                        for r in (row_view_ref.get("data") or []):
                                            if r.get("text") == row_txt and r.get("_guid"):
                                                guid_text = r.get("_guid"); break
                                    except Exception:
                                        pass
                        base_row = guid_to_row.get(guid_text)
                        if not base_row:
                            continue
                        for idx, key in enumerate(col_keys):
                            if key in ("text", "dimstyle", "LeaderGUID"):
                                continue
                            new_val = vals[idx] if idx < len(vals) else ""
                            old_val = base_row.get(key, "")
                            if str(new_val) != str(old_val):
                                changes += 1
                    try:
                        pending_count_lbl.Text = "Änderungen: {}".format(changes)
                    except Exception:
                        pass
                except Exception:
                    pass

            def on_cell_editing(sender, e):
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
                        try:
                            e.Cancel = True
                        except Exception:
                            pass
                except Exception:
                    pass
            try:
                grid.CellEditing += on_cell_editing
            except Exception:
                pass

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
                    new_val = None
                    if col_index < len(vals):
                        new_val = vals[col_index]
                    guid_text = None
                    try:
                        gidx = col_keys.index("LeaderGUID")
                        if gidx < len(vals):
                            guid_text = vals[gidx]
                    except Exception:
                        guid_text = None
                    if not guid_text:
                        try:
                            t_idx = col_keys.index("text")
                        except Exception:
                            t_idx = -1
                        if t_idx >= 0 and t_idx < len(vals):
                            row_txt = vals[t_idx]
                            if row_txt:
                                for r in (row_view_ref.get("data") or []):
                                    if r.get("text") == row_txt and r.get("_guid"):
                                        guid_text = r.get("_guid"); break
                    if not guid_text:
                        return
                    try:
                        import System
                        obj_id = System.Guid(guid_text)
                    except Exception:
                        obj_id = None
                    if obj_id is not None:
                        try:
                            _write_usertext_ui(obj_id, key, new_val)
                        except Exception:
                            pass
                    add_pending(guid_text, key, new_val)
                    try:
                        e.Item.Values = vals
                    except Exception:
                        pass
                    try:
                        update_change_counter()
                    except Exception:
                        pass
                except Exception:
                    pass
            try:
                grid.CellEdited += on_cell_edited
            except Exception:
                pass

            def on_cell_double(sender, e):
                try:
                    r = e.Row; col = e.Column
                    if r is None or col is None:
                        return
                    col_index = -1
                    try:
                        for i in range(len(grid.Columns)):
                            if grid.Columns[i] == col:
                                col_index = i; break
                    except Exception:
                        col_index = -1
                    if col_index < 0 or col_index >= len(col_keys):
                        return
                    key = col_keys[col_index]
                    if key in ("text", "dimstyle", "LeaderGUID"):
                        return
                    item = e.Item
                    if item is None:
                        return
                    vals = None
                    try:
                        vals = item.Values
                    except Exception:
                        vals = None
                    if vals is None:
                        return
                    # simple inline editor
                    try:
                        dlg = forms.Dialog(); dlg.Title = "Wert bearbeiten"
                        lay = forms.DynamicLayout(); lay.Padding = drawing.Padding(10); lay.Spacing = drawing.Size(6,6)
                        tb = forms.TextBox(); tb.Text = vals[col_index] if col_index < len(vals) else ""
                        lay.AddRow(tb)
                        okb = forms.Button(); okb.Text = "OK"
                        cb = forms.Button(); cb.Text = "Abbrechen"
                        def _ok(s,ev): dlg.Tag = tb.Text; dlg.Close()
                        def _cb(s,ev): dlg.Tag = None; dlg.Close()
                        okb.Click += _ok; cb.Click += _cb
                        lay.AddSeparateRow(None, okb, cb)
                        dlg.Content = lay; dlg.Tag = None
                        dlg.ShowModal()
                        new_val = dlg.Tag
                    except Exception:
                        new_val = None
                    if new_val is None:
                        return
                    try:
                        if col_index < len(vals):
                            vals[col_index] = new_val
                        else:
                            return
                    except Exception:
                        pass
                    try:
                        e.Item.Values = vals
                    except Exception:
                        pass
                    guid_text = None
                    try:
                        gidx = col_keys.index("LeaderGUID")
                        if gidx < len(vals):
                            guid_text = vals[gidx]
                    except Exception:
                        guid_text = None
                    if not guid_text:
                        try:
                            t_idx = col_keys.index("text")
                            row_txt = vals[t_idx] if t_idx < len(vals) else None
                            if row_txt:
                                for r in (row_view_ref.get("data") or []):
                                    if r.get("text") == row_txt and r.get("_guid"):
                                        guid_text = r.get("_guid"); break
                        except Exception:
                            pass
                    if guid_text:
                        add_pending(guid_text, key, new_val)
                        update_change_counter()
                except Exception:
                    pass

            def apply_filter_grid():
                try:
                    s = (search_tb.Text or "").strip().lower()
                    if not s:
                        row_view_ref["data"] = row_data
                        grid.DataStore = build_store(row_view_ref["data"]) ; return
                    filtered_rows = []
                    for r in row_data:
                        try:
                            joined = " ".join([str(v) for v in r.values() if v is not None]).lower()
                            if s in joined:
                                filtered_rows.append(r)
                        except Exception:
                            pass
                    row_view_ref["data"] = filtered_rows
                    grid.DataStore = build_store(filtered_rows)
                except Exception:
                    row_view_ref["data"] = row_data
                    grid.DataStore = build_store(row_view_ref["data"])        
            # keep a strong reference to event handlers to avoid GC in IronPython
            handler_refs = []
            def _on_search_changed(s, e):
                apply_filter_grid()
            handler_refs.append(_on_search_changed)
            search_tb.TextChanged += _on_search_changed
            row_view_ref["data"] = row_data
            grid.DataStore = build_store(row_view_ref["data"])

            try:
                grid_scroll = forms.Scrollable(); grid_scroll.Content = grid
                grid_scroll.ExpandContentWidth = True
                grid_scroll.ExpandContentHeight = False
                grid_page.Content = grid_scroll
            except Exception:
                grid_page.Content = grid
            tabs.Pages.Add(grid_page)
        except Exception as grid_ex:
            try:
                print("[Preview] Tabellenansicht deaktiviert:", grid_ex)
            except Exception:
                pass

        count_lbl = forms.Label();
        try:
            count_lbl.Text = "{} Leader in der Vorschau".format(len(leaders))
        except Exception:
            count_lbl.Text = "{} Leader in der Vorschau".format(len(leaders))
        layout.AddRow(count_lbl)

        try:
            scroll = forms.Scrollable(); scroll.Content = content_panel
            scroll.ExpandContentWidth = True
            scroll.ExpandContentHeight = False
            layout.AddRow(scroll)
        except Exception:
            layout.AddRow(content_panel)

        btn_export = forms.Button(); btn_export.Text = "Exportieren"
        btn_cancel = forms.Button(); btn_cancel.Text = "Abbrechen"
        btn_show = forms.Button(); btn_show.Text = "Element anzeigen"
        btn_commit = forms.Button(); btn_commit.Text = "Commit All"
        pending_count_lbl = forms.Label(); pending_count_lbl.Text = "Änderungen: 0"
        # Ensure buttons are enabled/visible
        try:
            btn_export.Enabled = True; btn_export.Visible = True
            btn_cancel.Enabled = True; btn_cancel.Visible = True
            btn_show.Enabled = True; btn_show.Visible = True
            btn_commit.Enabled = True; btn_commit.Visible = True
        except Exception:
            pass

        # safer close helper compatible with SemiModal and Modal dialogs
        def _safe_close(ok):
            try:
                dialog.Tag = bool(ok)
            except Exception:
                pass
            try:
                # Try direct close first (works for ShowModal)
                try:
                    dialog.Close();
                    return
                except Exception:
                    pass
                import Rhino
                # If dialog was opened via ShowSemiModal, prefer CloseSemiModal
                try:
                    Rhino.UI.EtoExtensions.CloseSemiModal(dialog)
                    return
                except Exception:
                    pass
                # Fallback: close on UI thread
                try:
                    import System
                    Rhino.RhinoApp.InvokeOnUiThread(System.Action(lambda: dialog.Close()))
                except Exception:
                    dialog.Close()
            except Exception:
                pass
        def on_export(sender, e):
            _dbg("[Preview] Export clicked")
            try:
                forms.MessageBox.Show("Export clicked")
            except Exception:
                pass
            _safe_close(True)
        def on_cancel(sender, e):
            _dbg("[Preview] Cancel clicked")
            try:
                forms.MessageBox.Show("Cancel clicked")
            except Exception:
                pass
            _safe_close(False)

        def on_show(sender, e):
            try:
                _dbg("[Preview] Show clicked")
                try:
                    forms.MessageBox.Show("Show clicked")
                except Exception:
                    pass
                sel = None
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
                guid_text = None
                if vals is not None:
                    try:
                        gidx = col_keys.index("LeaderGUID")
                        if gidx < len(vals):
                            guid_text = vals[gidx]
                    except Exception:
                        guid_text = None
                if not guid_text:
                    try:
                        tidx = col_keys.index("text")
                        txt = vals[tidx] if (vals and tidx < len(vals)) else None
                        if txt:
                            for r in (row_view_ref.get("data") or []):
                                if r.get("text") == txt and r.get("_guid"):
                                    guid_text = r.get("_guid"); break
                    except Exception:
                        pass
                if not guid_text:
                    return
                try:
                    import System
                    guid_obj = System.Guid(guid_text)
                except Exception:
                    guid_obj = None
                if guid_obj:
                    try:
                        rs.UnselectAllObjects()
                    except Exception:
                        pass
                    try:
                        rs.SelectObject(guid_obj); rs.ZoomSelected()
                    except Exception:
                        pass
            except Exception:
                pass
        # Helper to wire up handlers with diagnostics and a Command fallback
        def _wire_with_log(btn, handler, name):
            wired = False
            try:
                btn.Click += handler
                wired = True
                try:
                    print("[Preview] wired Click for", name)
                except Exception:
                    pass
            except Exception as ex:
                try:
                    print("[Preview] failed Click for", name, ":", ex)
                except Exception:
                    pass
            if not wired:
                try:
                    cmd = forms.Command()
                    def _exec(_s, _e):
                        try:
                            handler(_s, _e)
                        except Exception:
                            pass
                    cmd.Executed += _exec
                    btn.Command = cmd
                    handler_refs.append(_exec)
                    wired = True
                    try:
                        print("[Preview] wired Command for", name)
                    except Exception:
                        pass
                except Exception as ex2:
                    try:
                        print("[Preview] failed Command for", name, ":", ex2)
                    except Exception:
                        pass
            if wired:
                handler_refs.append(handler)
            return wired

        _wire_with_log(btn_export, on_export, "Exportieren")
        _wire_with_log(btn_cancel, on_cancel, "Abbrechen")
        _wire_with_log(btn_show, on_show, "Element anzeigen")

        def on_commit(sender, e):
            try:
                _dbg("[Preview] Commit clicked")
                try:
                    forms.MessageBox.Show("Commit clicked")
                except Exception:
                    pass
                total = 0
                # Commit changes from the visible grid back to Rhino user text
                try:
                    guid_idx = col_keys.index("LeaderGUID")
                except Exception:
                    guid_idx = -1
                try:
                    ds = grid.DataStore
                except Exception:
                    ds = None
                if ds is not None and guid_idx >= 0:
                    try:
                        import System
                        for it in ds:
                            try:
                                vals = it.Values
                            except Exception:
                                vals = None
                            if vals is None or guid_idx >= len(vals):
                                continue
                            gtxt = vals[guid_idx]
                            if not gtxt:
                                # Fallback via text value to map back to guid
                                try:
                                    t_idx = col_keys.index("text")
                                except Exception:
                                    t_idx = -1
                                if t_idx >= 0 and t_idx < len(vals):
                                    row_txt = vals[t_idx]
                                    if row_txt:
                                        try:
                                            for r in (row_view_ref.get("data") or []):
                                                if r.get("text") == row_txt and r.get("_guid"):
                                                    gtxt = r.get("_guid"); break
                                        except Exception:
                                            pass
                            if not gtxt:
                                continue
                            try:
                                obj_id = System.Guid(gtxt)
                            except Exception:
                                obj_id = None
                            if obj_id is None:
                                continue
                            base_row = guid_to_row.get(gtxt)
                            for c_index, key in enumerate(col_keys):
                                if key in ("text", "dimstyle", "LeaderGUID"):
                                    continue
                                new_val = vals[c_index] if c_index < len(vals) else ""
                                old_val = ""
                                try:
                                    if base_row is not None:
                                        old_val = base_row.get(key, "")
                                except Exception:
                                    old_val = ""
                                if str(new_val) != str(old_val):
                                    try:
                                        if _write_usertext_ui(obj_id, key, new_val):
                                            total += 1
                                            if base_row is not None:
                                                base_row[key] = "" if new_val is None else str(new_val)
                                    except Exception:
                                        pass
                    except Exception:
                        pass
                # also apply any pending changes captured from inline editors
                for gtxt, kv in list(pending_changes.items()):
                    try:
                        import System
                        obj_id = System.Guid(gtxt)
                    except Exception:
                        obj_id = None
                    if obj_id is None:
                        continue
                    for k, v in kv.items():
                        try:
                            if _write_usertext_ui(obj_id, k, v):
                                total += 1
                        except Exception:
                            pass
                pending_changes.clear()
                try:
                    pending_count_lbl.Text = "Änderungen: 0"
                except Exception:
                    pass
                try:
                    sc.doc.Views.Redraw()
                except Exception:
                    pass
                try:
                    print("[Preview] Commit: {} Werte in UserText geschrieben.".format(total))
                except Exception:
                    pass
            except Exception:
                pass
        _wire_with_log(btn_commit, on_commit, "Commit All")

        # Also bind Commands and add a toolbar as an alternative trigger path
        try:
            cmd_export = forms.Command(); cmd_export.MenuText = "Exportieren"; cmd_export.ToolBarText = "Exportieren"
            cmd_export.Executed += lambda s, e: on_export(s, e)
            btn_export.Command = cmd_export
        except Exception:
            pass
        try:
            cmd_cancel = forms.Command(); cmd_cancel.MenuText = "Abbrechen"; cmd_cancel.ToolBarText = "Abbrechen"
            cmd_cancel.Executed += lambda s, e: on_cancel(s, e)
            btn_cancel.Command = cmd_cancel
        except Exception:
            pass
        try:
            cmd_commit = forms.Command(); cmd_commit.MenuText = "Commit All"; cmd_commit.ToolBarText = "Commit All"
            cmd_commit.Executed += lambda s, e: on_commit(s, e)
            btn_commit.Command = cmd_commit
        except Exception:
            pass
        try:
            cmd_show = forms.Command(); cmd_show.MenuText = "Element anzeigen"; cmd_show.ToolBarText = "Anzeigen"
            cmd_show.Executed += lambda s, e: on_show(s, e)
            btn_show.Command = cmd_show
        except Exception:
            pass
        try:
            tb = forms.ToolBar()
            tb.Items.Add(cmd_export)
            tb.Items.Add(cmd_commit)
            tb.Items.Add(cmd_show)
            tb.Items.Add(cmd_cancel)
            dialog.ToolBar = tb
        except Exception:
            pass

        _dbg("[Preview] Buttons wired: export=", isinstance(btn_export, forms.Button), 
             ", cancel=", isinstance(btn_cancel, forms.Button), 
             ", show=", isinstance(btn_show, forms.Button), 
             ", commit=", isinstance(btn_commit, forms.Button))

        # also retain grid-related handlers to ensure they are not garbage collected
        try:
            handler_refs.extend([
                on_header_click,
                on_cell_editing,
                on_cell_edited,
                on_cell_double,
                apply_filter_grid,
                update_change_counter,
            ])
        except Exception:
            pass

        try:
            dialog._handler_refs = handler_refs
        except Exception:
            pass

        layout.AddSeparateRow(None, pending_count_lbl, btn_show, btn_commit, btn_export, btn_cancel)

        # designate default/abort buttons to improve behavior across Rhino/Eto versions
        try:
            dialog.DefaultButton = btn_export
        except Exception:
            pass
        try:
            dialog.AbortButton = btn_cancel
        except Exception:
            pass

        dialog.Content = layout
        dialog.Tag = False
        # Global key bindings (Enter=Export, Escape=Abbrechen) on dialog and main widgets
        try:
            def _on_key_down(s, e):
                try:
                    k = getattr(e, 'Key', None)
                    ks = str(k)
                except Exception:
                    ks = None
                if not ks:
                    return
                ks_l = ks.lower()
                try:
                    if ks_l.endswith('enter') or ks_l.endswith('return'):
                        on_export(s, e)
                    elif ks_l.endswith('escape'):
                        on_cancel(s, e)
                except Exception:
                    pass
            dialog.KeyDown += _on_key_down
            try:
                grid.KeyDown += _on_key_down
            except Exception:
                pass
            try:
                search_tb.KeyDown += _on_key_down
            except Exception:
                pass
            handler_refs.append(_on_key_down)
        except Exception:
            pass
        # Prefer modal ShowModal for reliable Close(); fall back to SemiModal if needed
        try:
            try:
                dialog.Owner = Rhino.UI.RhinoEtoApp.MainWindow
            except Exception:
                pass
            dialog.ShowModal()
        except Exception:
            try:
                Rhino.UI.EtoExtensions.ShowSemiModal(dialog, sc.doc, Rhino.UI.RhinoEtoApp.MainWindow)
            except Exception:
                try:
                    dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
                except Exception:
                    return True
        return bool(dialog.Tag)
    except Exception as e:
        try:
            print("[Preview] Fehler beim Aufbau der Vorschau:", e)
        except Exception:
            pass
        return True


