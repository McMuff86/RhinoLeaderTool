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
    print("[Preview] ========================================")
    print("[Preview] show_preview_dialog() called")
    print("[Preview] Number of leaders:", len(leaders) if leaders else 0)
    print("[Preview] Number of keys:", len(final_keys) if final_keys else 0)
    print("[Preview] ========================================")
    
    try:
        import rhinoscriptsyntax as rs
        import scriptcontext as sc
        import Rhino
        import Eto.Forms as forms
        import Eto.Drawing as drawing
        from rhino_sync import write_usertext_ui as _write_usertext_ui
        print("[Preview] All imports successful")
    except Exception as e:
        try:
            print("[Preview] UI imports failed:", e)
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
        
        try:
            # Larger dialog to accommodate content
            dialog.ClientSize = drawing.Size(1400, 700)
            print("[Preview] Set dialog ClientSize to 1400x700")
        except Exception as ex:
            print("[Preview] Failed to set ClientSize:", ex)
        try:
            dialog.MinimumSize = drawing.Size(900, 600)
            print("[Preview] Set dialog MinimumSize to 900x600")
        except Exception as ex:
            print("[Preview] Failed to set MinimumSize:", ex)
        try:
            dialog.Resizable = True
        except Exception:
            pass

        # CRITICAL: Create handler_refs at function scope to prevent GC
        handler_refs = []
        
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

        # Suchfeld für Tabellenansicht
        search_lbl = forms.Label(); search_lbl.Text = "Suche:"
        search_tb = forms.TextBox()
        try:
            search_tb.Size = drawing.Size(320, -1)
        except Exception:
            pass

        # Tabellenansicht
        grid = None
        try:
            grid = forms.TreeGridView()
            grid.ShowHeader = True
            grid.AllowMultipleSelection = False
            # Height will be controlled by Scrollable container
            try:
                grid.RowHeight = 22
            except Exception:
                pass
            row_data = list(rows)
            row_view_ref = {"data": row_data}
            col_keys = ["text", "dimstyle"]
            def add_col(idx, name, width=None):
                col = forms.GridColumn()
                col.HeaderText = name
                col.DataCell = forms.TextBoxCell(idx)
                
                # Set explicit width (CRITICAL for horizontal scrollbar)
                try:
                    if width is not None and width > 0:
                        col.Width = width
                    else:
                        col.Width = 120  # Default width
                    print("[Preview] Column '{}' width set to: {}".format(name, col.Width if width else 120))
                except Exception as ex:
                    print("[Preview] Failed to set column width for '{}': {}".format(name, ex))
                
                # Disable auto-sizing (CRITICAL - prevents auto-fit to container)
                try:
                    col.AutoSize = False
                    print("[Preview] Column '{}' AutoSize disabled".format(name))
                except Exception as ex:
                    print("[Preview] AutoSize not available for column '{}'".format(name))
                
                # Allow manual resizing
                try:
                    col.Resizable = True
                except Exception:
                    pass
                
                # Set editability
                try:
                    col.Editable = (name not in ("text", "dimstyle", "LeaderGUID"))
                except Exception:
                    pass
                
                # Enable sorting
                try:
                    col.Sortable = True
                except Exception:
                    pass
                
                grid.Columns.Add(col)
                return col
            add_col(0, "text", 260)
            add_col(1, "dimstyle", 180)
            max_cols = 40
            for i, k in enumerate(final_keys):
                if i >= max_cols:
                    break
                # Width is now set by default in add_col function
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
            # Store handler to prevent GC
            handler_refs.append(on_header_click)
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
            # Store handler to prevent GC
            handler_refs.append(on_cell_editing)
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
            # Store handler to prevent GC
            handler_refs.append(on_cell_edited)
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
            # Store handler to prevent GC
            handler_refs.append(on_cell_double)

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
            # Wire search handler
            def _on_search_changed(s, e):
                apply_filter_grid()
            handler_refs.append(_on_search_changed)
            search_tb.TextChanged += _on_search_changed
            row_view_ref["data"] = row_data
            grid.DataStore = build_store(row_view_ref["data"])

            # Grid is ready, will be added to main layout later
        except Exception as grid_ex:
            try:
                print("[Preview] Tabellenansicht deaktiviert:", grid_ex)
            except Exception:
                pass

        # BUILD MAIN LAYOUT using TableLayout for precise control
        print("[Preview] ===== Starting layout construction =====")
        count_lbl = forms.Label()
        try:
            count_lbl.Text = "{} Leader in der Vorschau".format(len(leaders))
            print("[Preview] Count label created:", count_lbl.Text)
        except Exception as ex:
            count_lbl.Text = "Leader in der Vorschau"
            print("[Preview] Failed to set count label text:", ex)
        
        # Configure grid for scrolling (TreeGridView has built-in scroll support)
        if grid is not None:
            try:
                # Don't set fixed width - let TreeGridView handle its own scrolling
                # Just ensure it has enough height
                try:
                    grid.Height = 450  # Fixed height to enable vertical scrollbar
                    print("[Preview] Set grid height to 450")
                except Exception as ex:
                    print("[Preview] Failed to set grid height:", ex)
            except Exception as ex:
                print("[Preview] Failed to configure grid:", ex)
        else:
            print("[Preview] WARNING: Grid is None!")
        
        # Create main layout with TableLayout for better control
        try:
            print("[Preview] Creating TableLayout...")
            main_table = forms.TableLayout()
            main_table.Padding = drawing.Padding(10)
            main_table.Spacing = drawing.Size(5, 5)
            print("[Preview] TableLayout created successfully")
        except Exception as ex:
            print("[Preview] CRITICAL: Failed to create TableLayout:", ex)
            import traceback
            traceback.print_exc()
            raise
        
        # Row 0: Count label
        try:
            print("[Preview] Adding count label row...")
            # TableRow needs TableCell, not raw controls!
            main_table.Rows.Add(forms.TableRow(forms.TableCell(count_lbl, scaleWidth=True)))
            print("[Preview] Count label row added")
        except Exception as ex:
            print("[Preview] ERROR adding count label:", ex)
            import traceback
            traceback.print_exc()
        
        # Row 1: Search box
        try:
            print("[Preview] Creating search box row...")
            # Create horizontal layout for search label + textbox
            search_row = forms.TableLayout()
            search_row.Spacing = drawing.Size(5, 5)
            search_row.Rows.Add(forms.TableRow(
                forms.TableCell(search_lbl),
                forms.TableCell(search_tb, scaleWidth=True)
            ))
            main_table.Rows.Add(forms.TableRow(forms.TableCell(search_row, scaleWidth=True)))
            print("[Preview] Search box added to layout")
        except Exception as ex:
            print("[Preview] ERROR adding search box:", ex)
            import traceback
            traceback.print_exc()
        
        # Row 2: Grid (scalable)
        if grid is not None:
            try:
                print("[Preview] Adding grid row...")
                # Grid needs to be in a TableCell, and the row should scale vertically
                grid_cell = forms.TableCell(grid, scaleWidth=True)
                grid_row = forms.TableRow(grid_cell)
                grid_row.ScaleHeight = True  # Allow this row to expand vertically
                main_table.Rows.Add(grid_row)
                print("[Preview] Grid added to layout")
            except Exception as ex:
                print("[Preview] ERROR adding grid:", ex)
                import traceback
                traceback.print_exc()
        else:
            print("[Preview] Skipping grid row (grid is None)")

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

        # Close handlers - set result BEFORE closing (Eto doesn't accept Close() argument)
        def on_export(sender, e):
            try:
                _dbg("[Preview] Export clicked")
                dialog.Tag = True  # Set return value
                dialog.Close()     # Close without argument
            except Exception as ex:
                try:
                    print("[Preview] Error closing dialog:", ex)
                except Exception:
                    pass
        
        def on_cancel(sender, e):
            try:
                _dbg("[Preview] Cancel clicked")
                dialog.Tag = False  # Set return value
                dialog.Close()      # Close without argument
            except Exception as ex:
                try:
                    print("[Preview] Error closing dialog:", ex)
                except Exception:
                    pass

        def on_show(sender, e):
            try:
                _dbg("[Preview] Show clicked")
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
        
        # Wire button handlers directly (store in handler_refs to prevent GC)
        handler_refs.extend([on_export, on_cancel, on_show])
        try:
            btn_export.Click += on_export
            print("[Preview] Export button wired")
        except Exception as ex:
            print("[Preview] Error wiring export button:", ex)
        
        try:
            btn_cancel.Click += on_cancel
            print("[Preview] Cancel button wired")
        except Exception as ex:
            print("[Preview] Error wiring cancel button:", ex)
        
        try:
            btn_show.Click += on_show
            print("[Preview] Show button wired")
        except Exception as ex:
            print("[Preview] Error wiring show button:", ex)

        def on_commit(sender, e):
            try:
                _dbg("[Preview] Commit clicked")
                total = 0
                # Commit changes from the visible grid back to Rhino user text
                try:
                    guid_idx = col_keys.index("LeaderGUID")
                    print("[Commit Debug] LeaderGUID index:", guid_idx)
                except Exception as ex:
                    guid_idx = -1
                    print("[Commit Debug] LeaderGUID not found in col_keys:", ex)
                try:
                    ds = grid.DataStore
                    print("[Commit Debug] DataStore retrieved:", ds is not None)
                except Exception as ex:
                    ds = None
                    print("[Commit Debug] Failed to get DataStore:", ex)
                if ds is not None and guid_idx >= 0:
                    print("[Commit Debug] Starting to process rows...")
                    try:
                        import System
                        # TreeGridStore is not directly iterable in Python - use Count and indexer
                        row_count = 0
                        try:
                            total_rows = ds.Count
                            print("[Commit Debug] DataStore has {} rows".format(total_rows))
                        except Exception:
                            # Fallback: try to get count another way or iterate differently
                            total_rows = 0
                            for item in ds:
                                total_rows += 1
                        
                        for i in range(total_rows):
                            row_count = i + 1
                            try:
                                it = ds[i]
                            except Exception as ex:
                                print("[Commit Debug] Failed to access row {}: {}".format(i, ex))
                                continue
                            try:
                                vals = it.Values
                            except Exception as ex:
                                vals = None
                                print("[Commit Debug] Row {}: Failed to get Values:".format(row_count), ex)
                            if vals is None or guid_idx >= len(vals):
                                print("[Commit Debug] Row {}: Skipping (vals={}, guid_idx={}, len={})".format(
                                    row_count, vals is not None, guid_idx, len(vals) if vals else 0))
                                continue
                            gtxt = vals[guid_idx]
                            print("[Commit Debug] Row {}: GUID={}".format(row_count, gtxt))
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
                            print("[Commit Debug] Row {}: base_row found: {}".format(row_count, base_row is not None))
                            changes_in_row = 0
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
                                    print("[Commit Debug] Row {}: Change detected in '{}': '{}' -> '{}'".format(
                                        row_count, key, old_val, new_val))
                                    try:
                                        write_result = _write_usertext_ui(obj_id, key, new_val)
                                        print("[Commit Debug] Row {}: _write_usertext_ui('{}', '{}') returned: {}".format(
                                            row_count, key, new_val, write_result))
                                        if write_result:
                                            total += 1
                                            changes_in_row += 1
                                            if base_row is not None:
                                                base_row[key] = "" if new_val is None else str(new_val)
                                            print("[Commit Debug] Row {}: Successfully wrote '{}' = '{}'".format(
                                                row_count, key, new_val))
                                        else:
                                            print("[Commit Debug] Row {}: ❌ Write FAILED for key '{}' (returned False)".format(row_count, key))
                                    except Exception as ex:
                                        print("[Commit Debug] Row {}: ❌ Exception writing '{}': {}".format(row_count, key, ex))
                            if changes_in_row == 0:
                                print("[Commit Debug] Row {}: No changes detected".format(row_count))
                    except Exception as ex:
                        print("[Commit Debug] Exception in main loop:", ex)
                else:
                    print("[Commit Debug] Skipped grid processing: ds={}, guid_idx={}".format(ds is not None, guid_idx))
                # also apply any pending changes captured from inline editors
                print("[Commit Debug] Pending changes:", len(pending_changes))
                for gtxt, kv in list(pending_changes.items()):
                    print("[Commit Debug] Pending change for GUID {}: {}".format(gtxt, kv))
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
                                print("[Commit Debug] Pending: Wrote {} = {}".format(k, v))
                        except Exception as ex:
                            print("[Commit Debug] Pending: Failed to write {} = {}: {}".format(k, v, ex))
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
        
        # Wire commit button handler
        handler_refs.append(on_commit)
        try:
            btn_commit.Click += on_commit
            print("[Preview] Commit button wired")
        except Exception as ex:
            print("[Preview] Error wiring commit button:", ex)

        # Create Commands for toolbar (without overriding Click handlers)
        cmd_export = None
        cmd_cancel = None
        cmd_commit = None
        cmd_show = None
        try:
            cmd_export = forms.Command(); cmd_export.MenuText = "Exportieren"; cmd_export.ToolBarText = "Exportieren"
            _cmd_export_handler = lambda s, e: on_export(s, e)
            cmd_export.Executed += _cmd_export_handler
            handler_refs.append(_cmd_export_handler)
        except Exception:
            pass
        try:
            cmd_cancel = forms.Command(); cmd_cancel.MenuText = "Abbrechen"; cmd_cancel.ToolBarText = "Abbrechen"
            _cmd_cancel_handler = lambda s, e: on_cancel(s, e)
            cmd_cancel.Executed += _cmd_cancel_handler
            handler_refs.append(_cmd_cancel_handler)
        except Exception:
            pass
        try:
            cmd_commit = forms.Command(); cmd_commit.MenuText = "Commit All"; cmd_commit.ToolBarText = "Commit All"
            _cmd_commit_handler = lambda s, e: on_commit(s, e)
            cmd_commit.Executed += _cmd_commit_handler
            handler_refs.append(_cmd_commit_handler)
        except Exception:
            pass
        try:
            cmd_show = forms.Command(); cmd_show.MenuText = "Element anzeigen"; cmd_show.ToolBarText = "Anzeigen"
            _cmd_show_handler = lambda s, e: on_show(s, e)
            cmd_show.Executed += _cmd_show_handler
            handler_refs.append(_cmd_show_handler)
        except Exception:
            pass
        # Add toolbar (optional alternative trigger path)
        try:
            tb = forms.ToolBar()
            if cmd_export: tb.Items.Add(cmd_export)
            if cmd_commit: tb.Items.Add(cmd_commit)
            if cmd_show: tb.Items.Add(cmd_show)
            if cmd_cancel: tb.Items.Add(cmd_cancel)
            dialog.ToolBar = tb
        except Exception:
            pass

        _dbg("[Preview] Buttons wired: export=", isinstance(btn_export, forms.Button), 
             ", cancel=", isinstance(btn_cancel, forms.Button), 
             ", show=", isinstance(btn_show, forms.Button), 
             ", commit=", isinstance(btn_commit, forms.Button))

        # Attach handler_refs to dialog to ensure they survive GC
        try:
            dialog._handler_refs = handler_refs
        except Exception:
            pass

        # Row 3: Buttons
        try:
            print("[Preview] Creating button row...")
            button_row = forms.TableLayout()
            button_row.Spacing = drawing.Size(5, 5)
            # All controls must be wrapped in TableCell!
            button_row.Rows.Add(forms.TableRow(
                forms.TableCell(None, scaleWidth=True),  # Stretcher to push buttons right
                forms.TableCell(pending_count_lbl),
                forms.TableCell(btn_show),
                forms.TableCell(btn_commit),
                forms.TableCell(btn_export),
                forms.TableCell(btn_cancel)
            ))
            main_table.Rows.Add(forms.TableRow(forms.TableCell(button_row, scaleWidth=True)))
            print("[Preview] Buttons added to layout")
        except Exception as ex:
            print("[Preview] ERROR adding buttons:", ex)
            import traceback
            traceback.print_exc()

        # designate default/abort buttons to improve behavior across Rhino/Eto versions
        try:
            dialog.DefaultButton = btn_export
            print("[Preview] Set DefaultButton")
        except Exception as ex:
            print("[Preview] Failed to set DefaultButton:", ex)
        try:
            dialog.AbortButton = btn_cancel
            print("[Preview] Set AbortButton")
        except Exception as ex:
            print("[Preview] Failed to set AbortButton:", ex)

        try:
            print("[Preview] Setting dialog.Content to main_table...")
            dialog.Content = main_table  # Use TableLayout instead of DynamicLayout
            dialog.Tag = False  # Initialize return value
            print("[Preview] Dialog content set successfully - ready to show!")
        except Exception as ex:
            print("[Preview] CRITICAL ERROR setting dialog.Content:", ex)
            import traceback
            traceback.print_exc()
            raise
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
        # Show modal dialog and get return value from dialog.Tag
        print("[Preview] ===== Attempting to show dialog =====")
        try:
            try:
                dialog.Owner = Rhino.UI.RhinoEtoApp.MainWindow
                print("[Preview] Dialog owner set to RhinoEtoApp.MainWindow")
            except Exception as ex:
                print("[Preview] Failed to set dialog owner:", ex)
            print("[Preview] Calling dialog.ShowModal()...")
            dialog.ShowModal()
            print("[Preview] Dialog closed normally")
        except Exception as show_ex:
            print("[Preview] ShowModal failed, trying alternatives:", show_ex)
            try:
                print("[Preview] Trying ShowSemiModal...")
                Rhino.UI.EtoExtensions.ShowSemiModal(dialog, sc.doc, Rhino.UI.RhinoEtoApp.MainWindow)
                print("[Preview] ShowSemiModal succeeded")
            except Exception as semi_ex:
                print("[Preview] ShowSemiModal failed:", semi_ex)
                try:
                    print("[Preview] Trying ShowModal with owner parameter...")
                    dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
                    print("[Preview] ShowModal with owner succeeded")
                except Exception as modal_ex:
                    print("[Preview] All dialog show methods failed:", modal_ex)
                    import traceback
                    traceback.print_exc()
                    return True
        # Return the value set in dialog.Tag by button handlers
        result = bool(dialog.Tag) if dialog.Tag is not None else True
        print("[Preview] Dialog result:", result)
        return result
    except Exception as e:
        try:
            print("[Preview] !!!!! CRITICAL ERROR beim Aufbau der Vorschau !!!!!")
            print("[Preview] Error type:", type(e).__name__)
            print("[Preview] Error message:", str(e))
            import traceback
            print("[Preview] Full traceback:")
            traceback.print_exc()
        except Exception as print_ex:
            print("[Preview] Could not print error details:", print_ex)
        return True


