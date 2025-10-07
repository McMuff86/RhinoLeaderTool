#! python 3
# r: xlsxwriter
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import Rhino.UI
import os
import json
from export_writer import write_txt_and_stats, write_xlsx
import re
from collections import defaultdict
from export_ui import show_preview_dialog as ui_show_preview


from config_io import load_config, get_base_path

## get_base_path now imported from config_io

def get_selected_csv_folder(cfg, prompt_if_missing=False):
    try:
        section = "RhinoLeaderToolGlobals"
        key = "CsvFolder"
        selected = None
        try:
            selected = rs.GetDocumentData(section, key)
        except Exception:
            selected = None
        if selected and os.path.isdir(selected):
            return selected
        if not prompt_if_missing:
            return None
        try:
            start_dir = (cfg.get("base_path") or get_base_path(cfg))
        except Exception:
            start_dir = get_base_path(cfg)
        try:
            folder = rs.BrowseForFolder(folder=start_dir, message="Select CSV folder for this document")
        except Exception:
            folder = None
        if folder and os.path.isdir(folder):
            try:
                rs.SetDocumentData(section, key, folder)
            except Exception:
                pass
            return folder
    except Exception:
        pass
    return None

def find_csv_in_tree(base_dir, csv_name):
    try:
        if not base_dir or not os.path.isdir(base_dir) or not csv_name:
            return None
        direct = os.path.join(base_dir, csv_name)
        if os.path.isfile(direct):
            return direct
        matches = []
        target_basename = os.path.basename(csv_name)
        for root, _dirs, files in os.walk(base_dir):
            for fn in files:
                if fn.lower() == target_basename.lower():
                    matches.append(os.path.join(root, fn))
        if not matches:
            return direct
        if len(matches) == 1:
            return matches[0]
        rels = [(m, os.path.relpath(m, base_dir)) for m in matches]
        rels.sort(key=lambda x: (len(x[1]), x[1].lower()))
        return rels[0][0]
    except Exception:
        return None

def read_csv_keys(csv_path):
    keys = []
    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",", 1)
                if len(parts) >= 1:
                    key = parts[0].strip()
                    if key and key not in keys:
                        keys.append(key)
    except Exception:
        pass
    return keys

def compute_required_keys_from_config(cfg):
    required = []
    try:
        base_path = get_selected_csv_folder(cfg, prompt_if_missing=False) or get_base_path(cfg)
        types_cfg = (cfg or {}).get("types", {})
        seen = set()
        for _typ, spec in types_cfg.items():
            csv_names = []
            try:
                if spec.get("csv"):
                    csv_names.append(spec.get("csv"))
            except Exception:
                pass
            # include preset CSVs as well so preset-only keys appear in UI/export
            try:
                for pr in (spec.get("presets") or []):
                    try:
                        pr_csv = pr.get("csv")
                        if pr_csv:
                            csv_names.append(pr_csv)
                    except Exception:
                        pass
            except Exception:
                pass
            for csv_name in csv_names:
                try:
                    if os.path.isabs(csv_name):
                        csv_path = csv_name
                    else:
                        csv_path = find_csv_in_tree(base_path, csv_name) or os.path.join(base_path, csv_name)
                    for key in read_csv_keys(csv_path):
                        if key not in seen:
                            seen.add(key)
                            required.append(key)
                except Exception:
                    pass
    except Exception:
        pass
    return required

def compute_document_only_keys(required_keys):
    extras = []
    try:
        req_set = set(required_keys or [])
        seen = set()
        for obj in sc.doc.Objects:
            try:
                geom = obj.Geometry
            except Exception:
                continue
            if isinstance(geom, Rhino.Geometry.Leader):
                try:
                    keys = obj.Attributes.GetUserStrings()
                except Exception:
                    keys = None
                if keys:
                    for k in keys.AllKeys:
                        if k in req_set:
                            continue
                        if k == "LeaderGUID":
                            continue
                        if k not in seen:
                            seen.add(k)
                            extras.append(k)
    except Exception:
        pass
    return sorted(extras)

def get_presets_store_path(cfg):
    try:
        base_dir = get_base_path(cfg)
        return os.path.join(base_dir, "export_presets.json")
    except Exception:
        return os.path.join(os.path.expanduser("~"), "export_presets.json")

def load_export_presets(cfg):
    # Bevorzugt aus globaler JSON-Datei; migriert ggf. bestehende DocData-Presets
    try:
        path = get_presets_store_path(cfg)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    # Migration aus DocData (falls vorhanden)
    try:
        section = "RhinoLeaderToolExportPresets"
        key = "KeySelectionPresets"
        docdata = rs.GetDocumentData(section, key)
        if docdata:
            try:
                migrated = json.loads(docdata)
                if isinstance(migrated, dict):
                    save_export_presets(cfg, migrated)
                    return migrated
            except Exception:
                pass
    except Exception:
        pass
    return {}

def save_export_presets(cfg, presets):
    try:
        path = get_presets_store_path(cfg)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(presets or {}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def choose_export_options(cfg, required_keys):
    try:
        print("[Export] Öffne Export-Dialog…")
        import Eto.Forms as forms
        import Eto.Drawing as drawing

        types_cfg = (cfg.get("types") or {})
        type_names = list(types_cfg.keys())
        has_types = bool(type_names)

        dialog = forms.Dialog()
        dialog.Title = "Export – Optionen"
        layout = forms.DynamicLayout()
        layout.Spacing = drawing.Size(6, 6)
        layout.Padding = drawing.Padding(10)

        cb_all = None
        cbx = {}
        if has_types:
            # 'Alle' Checkbox
            cb_all = forms.CheckBox()
            cb_all.Text = "Alle Typen"
            cb_all.Checked = True
            layout.AddRow(cb_all)

            # Typen-Checkboxen
            for name in type_names:
                cb = forms.CheckBox(); cb.Text = name
                cb.Checked = False
                cbx[name] = cb
                layout.AddRow(cb)

            def on_all_changed(sender, e):
                if bool(cb_all.Checked):
                    for n, c in cbx.items():
                        c.Checked = False
            cb_all.CheckedChanged += on_all_changed

            # Wenn ein einzelner Typ gewählt wird, 'Alle Typen' automatisch deaktivieren
            def make_on_type_changed(ctrl):
                def _handler(sender, e):
                    try:
                        if bool(ctrl.Checked) and cb_all is not None and bool(cb_all.Checked):
                            cb_all.Checked = False
                    except Exception:
                        pass
                return _handler
            for _n, _c in cbx.items():
                _c.CheckedChanged += make_on_type_changed(_c)

        # Export-Ziel (Desktop vs. Dokumentordner)
        layout.AddRow(None)
        rb_panel = forms.DynamicLayout(); rb_panel.Spacing = drawing.Size(6, 6)
        rb_desktop = forms.RadioButton(); rb_desktop.Text = "Desktop (Standardpfad)"
        # In Eto/IronPython RadioButtons must be grouped via constructor
        try:
            rb_doc = forms.RadioButton(rb_desktop)
        except Exception:
            rb_doc = forms.RadioButton()
            try:
                rb_doc.Group = rb_desktop
            except Exception:
                pass
        rb_doc.Text = "Ordner der 3dm-Datei"
        rb_desktop.Checked = True
        # Defensive fallback to keep exclusivity even if grouping isn't supported
        def _sync_group(_src, _dst):
            try:
                if bool(_src.Checked):
                    _dst.Checked = False
            except Exception:
                pass
        try:
            rb_desktop.CheckedChanged += lambda s, e: _sync_group(rb_desktop, rb_doc)
            rb_doc.CheckedChanged += lambda s, e: _sync_group(rb_doc, rb_desktop)
        except Exception:
            pass
        rb_panel.AddRow(rb_desktop)
        rb_panel.AddRow(rb_doc)
        lbl_path = forms.Label(); lbl_path.Text = "Zielpfad:"
        layout.AddRow(lbl_path, rb_panel)

        # Dateiname ohne Endung
        doc_name = sc.doc.Name or "leader"
        default_base = os.path.splitext(doc_name)[0] or "leader"
        name_tb = forms.TextBox(); name_tb.Text = default_base
        lbl_name = forms.Label(); lbl_name.Text = "Dateiname (ohne Endung):"
        layout.AddRow(lbl_name, name_tb)

        # Key-Auswahl (zweispaltig + scrollbar)
        layout.AddRow(None)
        keys_panel = forms.DynamicLayout(); keys_panel.Spacing = drawing.Size(6, 6)
        cb_all_keys = forms.CheckBox(); cb_all_keys.Text = "Alle UserText-Keys exportieren"; cb_all_keys.Checked = True
        keys_panel.AddRow(cb_all_keys)
        key_cbx = {}
        sorted_keys = sorted(required_keys)
        # document-only keys
        doc_only = compute_document_only_keys(required_keys)
        # Spalten aufteilen
        def build_two_columns(keys, default_checked=True):
            mid = (len(keys) + 1) // 2
            left = keys[:mid]
            right = keys[mid:]
            col_left = forms.DynamicLayout(); col_left.Spacing = drawing.Size(4, 4)
            col_right = forms.DynamicLayout(); col_right.Spacing = drawing.Size(4, 4)
            for k in left:
                cbk = forms.CheckBox(); cbk.Text = k; cbk.Checked = default_checked
                key_cbx[k] = cbk
                col_left.AddRow(cbk)
            for k in right:
                cbk = forms.CheckBox(); cbk.Text = k; cbk.Checked = default_checked
                key_cbx[k] = cbk
                col_right.AddRow(cbk)
            cols = forms.DynamicLayout(); cols.Spacing = drawing.Size(12, 6)
            cols.AddRow(col_left, col_right)
            return cols

        cols_csv = build_two_columns(sorted_keys, True)
        cols_doc = build_two_columns(doc_only, False) if doc_only else None

        tabs_keys = forms.TabControl()
        page_csv = forms.TabPage(); page_csv.Text = "CSV-Keys"; page_csv.Content = cols_csv
        tabs_keys.Pages.Add(page_csv)
        if cols_doc is not None:
            page_doc = forms.TabPage(); page_doc.Text = "Dokument-Keys"; page_doc.Content = cols_doc
            tabs_keys.Pages.Add(page_doc)

        scroll = forms.Scrollable(); scroll.Content = tabs_keys
        try:
            scroll.ExpandContentWidth = True
            scroll.ExpandContentHeight = False
        except Exception:
            pass
        try:
            scroll.Size = drawing.Size(420, 420)
        except Exception:
            pass
        def on_all_keys_changed(sender, e):
            all_on = bool(cb_all_keys.Checked)
            for _k, _cb in key_cbx.items():
                _cb.Enabled = not all_on
        cb_all_keys.CheckedChanged += on_all_keys_changed
        on_all_keys_changed(None, None)
        # Schnellaktionen
        btn_row = forms.DynamicLayout(); btn_row.Spacing = drawing.Size(6, 6)
        btn_all = forms.Button(); btn_all.Text = "Alle auswählen"
        btn_none = forms.Button(); btn_none.Text = "Keine auswählen"
        def on_select_all(sender, e):
            for _k, _cb in key_cbx.items():
                _cb.Checked = True
        def on_select_none(sender, e):
            for _k, _cb in key_cbx.items():
                _cb.Checked = False
        btn_all.Click += on_select_all; btn_none.Click += on_select_none
        btn_row.AddRow(btn_all, btn_none, None)
        lbl_keys = forms.Label(); lbl_keys.Text = "UserText-Keys:"
        keys_panel.AddRow(lbl_keys, scroll)
        keys_panel.AddRow(btn_row)
        layout.AddRow(keys_panel)

        # Presets
        layout.AddRow(None)
        presets = load_export_presets(cfg)
        preset_names = sorted(presets.keys())
        preset_panel = forms.DynamicLayout(); preset_panel.Spacing = drawing.Size(6, 6)
        preset_combo = forms.ComboBox()
        preset_combo.DataStore = preset_names
        preset_combo.SelectedIndex = 0 if len(preset_names) > 0 else -1
        def get_selected_preset_name():
            try:
                txt = preset_combo.Text or ""
                if txt and txt in preset_combo.DataStore:
                    return txt
            except Exception:
                pass
            try:
                idx = preset_combo.SelectedIndex
                if idx is not None and idx >= 0:
                    # DataStore kann ein .NET IEnumerable sein → in Liste umwandeln
                    try:
                        ds_list = list(preset_combo.DataStore)
                        if idx < len(ds_list):
                            return ds_list[idx]
                    except Exception:
                        pass
            except Exception:
                pass
            return None
        def apply_preset_by_name(pname):
            local = load_export_presets(cfg)
            p = local.get(pname)
            if not isinstance(p, dict):
                return
            use_all = bool(p.get("all_keys", p.get("all", False)))
            cb_all_keys.Checked = use_all
            if not use_all:
                wanted = set(p.get("keys") or [])
                for _k, _cb in key_cbx.items():
                    _cb.Checked = (_k in wanted)
            on_all_keys_changed(None, None)
            # Typen aus Preset übernehmen (falls vorhanden)
            if has_types:
                types_all = bool(p.get("types_all", False))
                preset_types = p.get("types") or []
                if types_all or not preset_types:
                    cb_all.Checked = True
                    on_all_changed(None, None)
                else:
                    cb_all.Checked = False
                    wanted_types = set(preset_types)
                    for _name, _cb in cbx.items():
                        _cb.Checked = (_name in wanted_types)
            try:
                dialog.Invalidate()
            except Exception:
                pass
        def on_preset_changed(sender, e):
            try:
                name = get_selected_preset_name()
                if not name:
                    return
                apply_preset_by_name(name)
            except Exception:
                pass
        preset_combo.SelectedIndexChanged += on_preset_changed
        # Falls es genau ein Preset gibt, direkt Auswahl in die UI übernehmen
        try:
            if len(preset_names) == 1:
                apply_preset_by_name(preset_names[0])
        except Exception:
            pass

        save_name_tb = forms.TextBox(); save_name_tb.Text = ""
        btn_save = forms.Button(); btn_save.Text = "Preset speichern"
        btn_delete = forms.Button(); btn_delete.Text = "Preset löschen"
        def on_save(sender, e):
            name = (save_name_tb.Text or "").strip()
            if not name:
                return
            try:
                sel_all = bool(cb_all_keys.Checked)
                sel_keys = [k for k, cb in key_cbx.items() if bool(cb.Checked)]
                # Typen erfassen
                types_all = True
                sel_types = []
                if has_types:
                    types_all = bool(cb_all.Checked)
                    if not types_all:
                        sel_types = [t for t, c in cbx.items() if bool(c.Checked)]
                        if not sel_types:
                            types_all = True
                entry = {
                    "all_keys": bool(sel_all),
                    "keys": sel_keys if not sel_all else [],
                    "types_all": bool(types_all),
                    "types": sel_types if not types_all else [],
                }
                local = load_export_presets(cfg)
                local[name] = entry
                save_export_presets(cfg, local)
                # refresh combo
                new_names = sorted(local.keys())
                preset_combo.DataStore = new_names
                try:
                    preset_combo.SelectedIndex = new_names.index(name)
                except Exception:
                    preset_combo.SelectedIndex = -1
                # sofort anwenden
                apply_preset_by_name(name)
            except Exception:
                pass
        def on_delete(sender, e):
            try:
                pname = get_selected_preset_name()
                if not pname:
                    return
                local = load_export_presets(cfg)
                if pname in local:
                    del local[pname]
                    save_export_presets(cfg, local)
                    new_names = sorted(local.keys())
                    preset_combo.DataStore = new_names
                    preset_combo.SelectedIndex = -1
            except Exception:
                pass
        btn_save.Click += on_save; btn_delete.Click += on_delete
        lbl_presets = forms.Label(); lbl_presets.Text = "Presets:"
        btn_load = forms.Button(); btn_load.Text = "Preset laden"
        def on_load(sender, e):
            try:
                idx = preset_combo.SelectedIndex
                if idx is None or idx < 0:
                    return
                ds = preset_combo.DataStore
                try:
                    name = ds[idx]
                except Exception:
                    return
                apply_preset_by_name(name)
                # Synchronisiere UI explizit
                try:
                    dialog.Content = layout
                    dialog.Invalidate()
                except Exception:
                    pass
            except Exception:
                pass
        btn_load.Click += on_load
        preset_panel.AddRow(lbl_presets, preset_combo, btn_load)
        preset_panel.AddRow(save_name_tb, btn_save, btn_delete)
        layout.AddRow(preset_panel)

        # Vorschau-Option
        layout.AddRow(None)
        cb_preview = forms.CheckBox(); cb_preview.Text = "Vorschau vor Export anzeigen"; cb_preview.Checked = True
        layout.AddRow(cb_preview)

        layout.AddRow(None)
        ok_btn = forms.Button(); ok_btn.Text = "OK"
        cancel_btn = forms.Button(); cancel_btn.Text = "Abbrechen"
        layout.AddSeparateRow(None, ok_btn, cancel_btn)

        def on_ok(sender, e):
            dialog.Tag = True
            dialog.Close()
        def on_cancel(sender, e):
            dialog.Tag = False
            dialog.Close()
        ok_btn.Click += on_ok; cancel_btn.Click += on_cancel

        dialog.Content = layout
        dialog.Tag = False
        # Zeige Dialog; versuche zuerst ohne Owner (robuster in manchen Rhino-Versionen)
        try:
            dialog.ShowModal()
        except Exception as modal2_ex:
            print("[Export] Dialog.ShowModal ohne Owner fehlgeschlagen:", modal2_ex)
            try:
                Rhino.UI.EtoExtensions.ShowSemiModal(dialog, sc.doc, Rhino.UI.RhinoEtoApp.MainWindow)
            except Exception as semimodal_ex:
                print("[Export] EtoExtensions.ShowSemiModal fehlgeschlagen:", semimodal_ex)
                try:
                    dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
                except Exception as modal_ex:
                    print("[Export] Dialog.ShowModal mit Owner fehlgeschlagen:", modal_ex)
                    return None

        if not dialog.Tag:
            print("[Export] Dialog abgebrochen")
            return None

        # Determine selection and overrides
        use_standard = True if bool(rb_desktop.Checked) else False
        base_name = (name_tb.Text or "leader").strip() or "leader"
        # Keys selection
        export_all_keys = bool(cb_all_keys.Checked)
        selected_keys = None
        if not export_all_keys:
            selected_keys = [k for k, cb in key_cbx.items() if bool(cb.Checked)]
        if not has_types:
            return [], use_standard, base_name, export_all_keys, selected_keys, bool(cb_preview.Checked)
        selected_types = [n for n, c in cbx.items() if bool(c.Checked)]
        if (cb_all is not None and bool(cb_all.Checked)) or not selected_types:
            return [], use_standard, base_name, export_all_keys, selected_keys, bool(cb_preview.Checked)
        styles = []
        for t in selected_types:
            dim = types_cfg.get(t, {}).get("dimstyle")
            if dim:
                styles.append(dim)
        print("[Export] Auswahl:", styles if styles else "Alle Typen", ", Pfad Standard?", use_standard, ", Name:", base_name)
        return styles, use_standard, base_name, export_all_keys, selected_keys, bool(cb_preview.Checked)
    except Exception as e:
        print("[Export] Fehler im Dialog:", e)
        return None

def normalize_value_for_excel(value, na_value):
    try:
        if value is None:
            return na_value
        if isinstance(value, (int, float)):
            return value
        s = str(value).strip()
        if s == "" or s.upper() == str(na_value).upper():
            return na_value
        # try int
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
        # try float (dot or comma)
        s2 = s.replace(",", ".")
        # must contain only one dot and digits otherwise leave text
        import re
        if re.fullmatch(r"-?\d+\.\d+", s2):
            return float(s2)
        return value
    except Exception:
        return value

def parse_floor_rank(text):
    # Returns a tuple (rank, normalized) where lower rank sorts first
    try:
        if text is None:
            return (10_000, "")
        s = str(text).strip().upper()
        if s == "":
            return (10_000, "")
        # Patterns:
        # UGxxx (UG, UG-1, UG1, UG2, UG03...)
        m = re.match(r"^UG\s*([-+]?\d+)?", s)
        if m:
            n = m.group(1)
            num = int(n) if n is not None else 1
            # more negative (deeper basement) should come first → lower floors first
            return (-1000 + num, s)
        # E-1, E0, E1, E2 ...
        m = re.match(r"^E\s*([-+]?\d+)", s)
        if m:
            num = int(m.group(1))
            return (num, s)
        # EGxxx or EG
        if s.startswith("EG"):
            # treat EG as 0
            return (0, s)
        # 1OG, 2OG, 10OG ...
        m = re.match(r"^([0-9]+)\s*OG", s)
        if m:
            num = int(m.group(1))
            return (num, s)
        # fallback: try to parse any int in string
        m = re.search(r"-?\d+", s)
        if m:
            return (int(m.group(0)), s)
        return (10_000, s)
    except Exception:
        return (10_000, str(text))

def load_export_sorting_rules(cfg):
    try:
        base_dir = get_base_path(cfg)
        path = os.path.join(base_dir, "export_sorting.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return None

def compute_floor_rank_with_rules(text, rules):
    try:
        s = ("" if text is None else str(text)).strip()
        if s == "":
            return None
        patterns = rules.get("patterns") or []
        for rule in patterns:
            try:
                rx = rule.get("regex")
                if not rx:
                    continue
                m = re.search(rx, s, re.IGNORECASE)
                if not m:
                    continue
                if "group" in rule:
                    grp_index = int(rule.get("group", 1))
                    base = int(rule.get("base", 0))
                    num = int(m.group(grp_index))
                    return base + num
                if "rank" in rule:
                    return int(rule.get("rank"))
                # fallback: try first group numeric
                if m.groups():
                    try:
                        return int(m.group(1))
                    except Exception:
                        pass
                # if match but nothing defined, return 0 to keep matched top
                return 0
            except Exception:
                continue
        # fallback behavior
        fb = rules.get("fallback") or {}
        if fb.get("extract_int", True):
            m = re.search(r"-?\d+", s)
            if m:
                return int(m.group(0))
        return int(fb.get("fallback_rank", 10_000))
    except Exception:
        return None

def compute_floor_rank(text, cfg, rules):
    try:
        if rules and (rules.get("enabled", True)):
            return compute_floor_rank_with_rules(text, rules)
    except Exception:
        pass
    # fallback heuristic
    r = parse_floor_rank(text)
    return r[0] if isinstance(r, tuple) else r

def _write_usertext_ui(obj_id, key, val):
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

def _normalize_key(name):
    try:
        if name is None:
            return ""
        s = str(name).strip().lower()
        # remove BOM and hidden whitespace
        try:
            s = s.replace(u"\ufeff", "")
        except Exception:
            pass
        # replace german umlauts for tolerant matches
        s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        s = s.replace("ß", "ss")
        s = s.replace(" ", "_")
        # collapse underscores so variants with/without '_' match equally
        s = s.replace("_", "")
        return s
    except Exception:
        return ""

def _normalize_int_from_string(text):
    try:
        if text is None:
            return None
        s = str(text).strip()
        if s == "":
            return None
        import re
        m = re.search(r"-?\d+", s.replace(",", "."))
        if not m:
            return None
        return int(m.group(0))
    except Exception:
        return None

def _get_user_value(user_dict, candidate_keys):
    try:
        if not isinstance(user_dict, dict):
            return None, None
        norm_map = { _normalize_key(k): k for k in user_dict.keys() }
        for c in candidate_keys:
            n = _normalize_key(c)
            if n in norm_map:
                real_key = norm_map[n]
                return real_key, user_dict.get(real_key)
    except Exception:
        pass
    return None, None

def _is_debug_calc_enabled(cfg):
    try:
        return bool((cfg.get("export") or {}).get("debug_calc", False))
    except Exception:
        return False

def _is_override_bandmass_enabled(cfg):
    try:
        exp = (cfg.get("export") or {})
        # support both spellings
        if "override_bandmasse" in exp:
            return bool(exp.get("override_bandmasse"))
        if "override_bandmass" in exp:
            return bool(exp.get("override_bandmass"))
        return False
    except Exception:
        return False

def load_elkuch_mapping(cfg):
    try:
        base_dir = get_base_path(cfg)
        filename = "Anordnung_Band_Schloss_Elkuch.CSV"
        candidates = []
        try:
            candidates.append(os.path.join(base_dir, filename))
        except Exception:
            pass
        # also probe selected CSV folder and tree search as fallback
        try:
            sel_dir = get_selected_csv_folder(cfg, prompt_if_missing=False)
        except Exception:
            sel_dir = None
        if sel_dir:
            try:
                candidates.append(os.path.join(sel_dir, filename))
            except Exception:
                pass
        # tree search
        try:
            found = find_csv_in_tree(base_dir, filename)
            if found and found not in candidates:
                candidates.append(found)
        except Exception:
            pass
        if sel_dir:
            try:
                found2 = find_csv_in_tree(sel_dir, filename)
                if found2 and found2 not in candidates:
                    candidates.append(found2)
            except Exception:
                pass
        csv_path = None
        for c in candidates:
            try:
                if c and os.path.isfile(c):
                    csv_path = c; break
            except Exception:
                continue
        if not csv_path:
            if _is_debug_calc_enabled(cfg):
                try:
                    print("[Calc] Elkuch mapping file not found. Tried:")
                    for c in candidates:
                        print("   -", c)
                except Exception:
                    pass
            return None
        mapping = {}
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        if not lines:
            return None
        header = [h.strip() for h in lines[0].split(";")]
        # indices
        def idx_of(names):
            norm = [_normalize_key(x) for x in header]
            for want in names:
                w = _normalize_key(want)
                if w in norm:
                    return norm.index(w)
            return -1
        idx_h = idx_of(["lichte_höhe", "lichte_hoehe", "lichthöhe", "lichthohe"]) 
        idx_b = idx_of(["b"])
        idx_c = idx_of(["c"])
        idx_d = idx_of(["d"])
        idx_m = idx_of(["m"])  # optional middle column
        if min(idx_h, idx_b, idx_c, idx_d) < 0:
            if _is_debug_calc_enabled(cfg):
                try:
                    print("[Calc] Elkuch header not recognized:", header)
                except Exception:
                    pass
            return None
        for ln in lines[1:]:
            parts = [p.strip() for p in ln.split(";")]
            if idx_h >= len(parts):
                continue
            hval = _normalize_int_from_string(parts[idx_h])
            if hval is None:
                continue
            def safe_get(i):
                try:
                    return parts[i]
                except Exception:
                    return ""
            row = {"B": safe_get(idx_b), "C": safe_get(idx_c), "D": safe_get(idx_d)}
            if idx_m >= 0 and idx_m < len(parts):
                row["M"] = safe_get(idx_m)
            mapping[hval] = row
        return mapping
    except Exception:
        return None

def autofill_band_masses_for_export(leaders, cfg):
    try:
        mapping = load_elkuch_mapping(cfg)
        if not mapping:
            if _is_debug_calc_enabled(cfg):
                print("[Calc] Elkuch mapping not found – skip.")
            return
        for it in leaders:
            try:
                user = it.get("user") or {}
                leader_name = it.get("text", "")
                # Read band count and height
                _key_ba, band_count_val = _get_user_value(user, ["Bandanzahl", "Band_anzahl", "bandanzahl"])
                _key_h, height_val = _get_user_value(user, ["Lichthöhe", "lichte_höhe", "lichthohe", "lichte_hoehe"])
                # Bandanzahl kann auch "calc" sein → dann aus Mapping nur Bandmasse berechnen,
                # Bandanzahl selbst bleibt wie gesetzt (calc oder vorhandener Wert)
                if height_val is None:
                    if _is_debug_calc_enabled(cfg):
                        print("[Calc] {}: skip – Lichthöhe missing".format(leader_name))
                    continue
                band_count = _normalize_int_from_string(band_count_val)
                hnorm = _normalize_int_from_string(height_val)
                if hnorm is None:
                    if _is_debug_calc_enabled(cfg):
                        print("[Calc] {}: skip – Lichthöhe unparsable: {}".format(leader_name, height_val))
                    continue
                row = mapping.get(hnorm)
                if not row:
                    if _is_debug_calc_enabled(cfg):
                        print("[Calc] {}: skip – no Elkuch row for height {}".format(leader_name, hnorm))
                    continue
                # Detect any present bandmass keys, tolerant to naming (Bandmass_1_c, Bandmass1_c, Bandmass1c, Bandmass3_m, ...)
                def is_calc(x):
                    try:
                        return str(x).strip().lower() == "calc"
                    except Exception:
                        return False
                norm_to_real = { _normalize_key(k): k for k in (user.keys() if isinstance(user, dict) else []) }
                present = []
                for nk, real in norm_to_real.items():
                    # expect pattern bandmass{index}{letter}
                    if not nk.startswith("bandmass"):
                        continue
                    rest = nk[len("bandmass"):]
                    # rest like '1c' or '1_c' collapsed already
                    if len(rest) < 2:
                        continue
                    idx_char = rest[0]
                    if idx_char not in ("1", "2", "3"):
                        continue
                    letter = rest[1:2]
                    present.append((idx_char, letter.lower(), real, user.get(real)))
                # If override is enabled and no bandmass keys exist, we still want to provide values in export
                override_all = _is_override_bandmass_enabled(cfg)
                if not present and not override_all:
                    if _is_debug_calc_enabled(cfg):
                        print("[Calc] {}: skip – no Bandmass* calc targets present".format(leader_name))
                    continue

                def fill_for(idx, letter_target, value):
                    # idx: '1','2','3'; letter_target one of 'c','b','d','m'
                    # Strategy: if a matching key for this index exists, set that; otherwise set canonical key
                    target_assigned = False
                    changed_local = 0
                    for i, lt, real_key, cur in present:
                        if i != idx:
                            continue
                        if (not override_all) and (not is_calc(cur)):
                            continue
                        # If actual key suffix is 'm' and we have M → prefer M
                        prev = user.get(real_key)
                        if lt == 'm' and 'M' in row:
                            user[real_key] = row.get('M', "")
                        elif lt == 'd':
                            user[real_key] = row.get('D', "")
                        elif lt == 'b':
                            user[real_key] = row.get('B', "")
                        elif lt == 'c':
                            user[real_key] = row.get('C', "")
                        else:
                            user[real_key] = value
                        if str(prev) != str(user.get(real_key)):
                            changed_local += 1
                        target_assigned = True
                    if override_all and not target_assigned:
                        # assign canonical fallback key even if it didn't exist
                        canonical = {
                            ('1','c'): 'Bandmass_1_c',
                            ('2','b'): 'Bandmass_2_b',
                            ('3','d'): 'Bandmass_3_d',
                            ('3','m'): 'Bandmass_3_m',
                        }.get((idx, letter_target))
                        if canonical:
                            prev = user.get(canonical)
                            user[canonical] = value
                            if str(prev) != str(value):
                                changed_local += 1
                    return changed_local

                changed = 0
                if band_count == 2:
                    changed += fill_for('1', 'c', row.get('C', ""))
                    changed += fill_for('2', 'b', row.get('B', ""))
                    # for 3rd, set None if present and calc
                    for i, lt, real_key, cur in present:
                        if i != '3':
                            continue
                        if (override_all or is_calc(cur)):
                            user[real_key] = "None"; changed += 1
                    if override_all and not any(i=='3' for i,_,_,_ in present):
                        user['Bandmass_3_d'] = "None"; changed += 1
                elif band_count == 3:
                    changed += fill_for('1', 'c', row.get('C', ""))
                    changed += fill_for('2', 'b', row.get('B', ""))
                    # 3rd: prefer D, but if key ends with 'm' use M
                    if any(i=='3' for i,_,_,_ in present):
                        for i, lt, real_key, cur in present:
                            if i != '3':
                                continue
                            if (override_all or is_calc(cur)):
                                if lt == 'm' and 'M' in row:
                                    user[real_key] = row.get('M', ""); changed += 1
                                else:
                                    user[real_key] = row.get('D', ""); changed += 1
                    else:
                        # no key present → create canonical depending on availability of M
                        if 'M' in row:
                            user['Bandmass_3_m'] = row.get('M', ""); changed += 1
                        else:
                            user['Bandmass_3_d'] = row.get('D', ""); changed += 1
                else:
                    # Unknown band_count (e.g., calc) → fill 1:C, 2:B, 3:None/D based on key letter
                    changed += fill_for('1', 'c', row.get('C', ""))
                    changed += fill_for('2', 'b', row.get('B', ""))
                    third_set = False
                    for i, lt, real_key, cur in present:
                        if i != '3':
                            continue
                        if (override_all or is_calc(cur)):
                            if lt == 'm' and 'M' in row:
                                user[real_key] = row.get('M', ""); changed += 1; third_set = True
                            else:
                                user[real_key] = "None"; changed += 1; third_set = True
                    if override_all and not third_set:
                        user['Bandmass_3_d'] = "None"; changed += 1
                if _is_debug_calc_enabled(cfg):
                    try:
                        band_vals = {k: user[k] for k in user.keys() if _normalize_key(k).startswith('bandmass')}
                        if changed > 0:
                            print("[Calc] {}: filled band masses (count={}) : {}".format(leader_name, band_count_val, band_vals))
                        else:
                            print("[Calc] {}: no changes (override={}) : {}".format(leader_name, _is_override_bandmass_enabled(cfg), band_vals))
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass

def _get_csv_keys_for_styles(cfg, styles):
    try:
        if not styles:
            return []
        types_cfg = (cfg or {}).get("types", {})
        base_path = get_selected_csv_folder(cfg, prompt_if_missing=False) or get_base_path(cfg)
        order = []
        seen = set()
        for name, spec in types_cfg.items():
            try:
                dim = spec.get("dimstyle")
                if dim not in styles:
                    continue
                csv_name = spec.get("csv")
                if not csv_name:
                    continue
                if os.path.isabs(csv_name):
                    csv_path = csv_name
                else:
                    csv_path = find_csv_in_tree(base_path, csv_name) or os.path.join(base_path, csv_name)
                for k in read_csv_keys(csv_path):
                    if k not in seen:
                        seen.add(k)
                        order.append(k)
            except Exception:
                pass
        return order
    except Exception:
        return []

def _reorder_final_keys(cfg, final_keys, target_styles):
    try:
        if not final_keys:
            return final_keys
        leader_guid_last = "LeaderGUID" in final_keys
        remaining = [k for k in final_keys if k != "LeaderGUID"]
        preferred = _get_csv_keys_for_styles(cfg, target_styles)
        ordered = []
        if preferred:
            for k in preferred:
                if k in remaining and k not in ordered:
                    ordered.append(k)
            # append any leftover alphabetically
            leftovers = [k for k in remaining if k not in ordered]
            leftovers.sort(key=lambda s: s.lower())
            ordered.extend(leftovers)
        else:
            # No specific styles selected → alphabetical
            ordered = sorted(remaining, key=lambda s: s.lower())
        if leader_guid_last:
            ordered.append("LeaderGUID")
        return ordered
    except Exception:
        return final_keys

def export_leader_texts(mode=None):
    cfg = load_config()
    # Ziel-Bemaßungsstile (per Dialog auswählbar) + optionale Pfadangaben
    target_styles = cfg.get("export", {}).get("target_styles", [])
    # Erforderliche Keys aus allen CSV-Dateien (Union)
    required_keys = compute_required_keys_from_config(cfg)
    picked = choose_export_options(cfg, required_keys)
    use_standard_override = None
    base_name_override = None
    export_all_keys = True
    selected_keys = None
    preview_before_export = True
    if picked is not None:
        if isinstance(picked, tuple) and len(picked) >= 3:
            styles = picked[0]
            use_standard_override = picked[1]
            base_name_override = picked[2]
            if len(picked) >= 5:
                export_all_keys = bool(picked[3])
                selected_keys = picked[4]
            if len(picked) >= 6:
                preview_before_export = bool(picked[5])
            target_styles = styles  # [] => export all
        elif isinstance(picked, list):
            target_styles = picked
    else:
        print("[Export] Export-Dialog konnte nicht angezeigt werden – verwende ggf. Konsolenabfragen oder Defaults.")

    def get_export_paths(active_mode, prompt_user=True, use_standard_override=None, base_name_override=None):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        use_standard = True
        if use_standard_override is not None:
            use_standard = bool(use_standard_override)
        elif prompt_user:
            # True = Standard (Desktop), False = Dokument-Ordner
            res = rs.GetBoolean("Export to standard Desktop path?", ("StandardPath", "No", "Yes"), True)
            if res is not None and len(res) > 0:
                use_standard = bool(res[0])
        if use_standard:
            base_dir = desktop_path
            base_name = base_name_override or "leader"
        else:
            # Dokumentpfad verwenden
            doc_path = sc.doc.Path or ""
            doc_name = sc.doc.Name or "leader"
            if doc_path:
                base_dir = os.path.dirname(doc_path)
            else:
                # Fallback auf Desktop, wenn Datei ungespeichert
                base_dir = desktop_path
            base_name = (base_name_override or os.path.splitext(doc_name)[0] or "leader")

        if prompt_user and (base_name_override is None):
            try:
                default_name = base_name
                entered = rs.GetString("Dateiname (ohne Endung)", default_name)
                if entered and entered.strip():
                    base_name = entered.strip()
            except Exception:
                pass

        output_path_txt = os.path.join(base_dir, f"{base_name}_leader_texts.txt")
        output_path_stats = os.path.join(base_dir, f"{base_name}_leader_stats.txt")
        output_path_xlsx = os.path.join(base_dir, f"{base_name}_leader_export.xlsx")
        return output_path_txt, output_path_stats, output_path_xlsx

    # Sammellisten
    export_lines_text = []
    leaders = []  # strukturierte Liste für XLSX
    all_user_keys = []  # zusätzlich entdeckte Keys (nicht in required)
    style_counts = defaultdict(int)

    for obj in sc.doc.Objects:
        try:
            geom = obj.Geometry
        except Exception:
            continue
        # Robuste Erkennung eines Leaders über die Geometrie
        if isinstance(geom, Rhino.Geometry.Leader):
            leader = geom
            dimstyle_id = leader.DimensionStyleId
            dimstyle = sc.doc.DimStyles.FindId(dimstyle_id)

            # Wenn keine Zielstile konfiguriert sind: alle akzeptieren
            style_ok = True if not target_styles else (dimstyle is not None and dimstyle.Name in target_styles)
            if style_ok:
                # Basis-Text
                text = leader.Text.replace('\r\n', ' ').replace('\n', ' ')
                
                # UserText ermitteln (als Dict und Text)
                user_text_pairs = []
                user_dict = {}
                keys = obj.Attributes.GetUserStrings()
                if keys:
                    for key in keys.AllKeys:
                        # optional Filter anhand Dialogauswahl
                        if (not export_all_keys) and (selected_keys is not None) and (key not in selected_keys):
                            continue
                        value = keys[key]
                        user_text_pairs.append(f"{key}={value}")
                        if key not in user_dict:
                            user_dict[key] = value
                        if key not in all_user_keys:
                            all_user_keys.append(key)

                # LeaderGUID sicherstellen
                leader_guid = str(obj.Id)
                if "LeaderGUID" not in user_dict or not user_dict.get("LeaderGUID"):
                    user_dict["LeaderGUID"] = leader_guid
                # Stelle sicher, dass LeaderGUID am Ende in den Spalten ist (falls nicht in required)
                if "LeaderGUID" not in required_keys and "LeaderGUID" not in all_user_keys:
                    all_user_keys.append("LeaderGUID")

                # TXT-Zeile aufbauen
                full_line = text
                if user_text_pairs:
                    full_line += " | " + " | ".join(user_text_pairs)

                # add optional floor sort rank for known keys
                floor_rank = None
                try:
                    if (cfg.get("export", {}).get("floor_sort", False)):
                        rules = load_export_sorting_rules(cfg)
                        # per user: source = leader text
                        floor_rank = compute_floor_rank(text, cfg, rules)
                except Exception:
                    floor_rank = None

                export_lines_text.append(full_line)
                leaders.append({
                    "text": text,
                    "dimstyle": dimstyle.Name,
                    "user": user_dict,
                    "_floor_rank": floor_rank
                })
                style_name = dimstyle.Name if dimstyle else "Unknown"
                style_counts[style_name] += 1

    # Ausgabe
    if not leaders:
        print("Keine passenden Leader gefunden.")
        return

    # finale Keys: zuerst required, dann zusätzlich entdeckte; ggf. durch Nutzerfilter einschränken
    final_keys = list(required_keys)
    for k in all_user_keys:
        if k not in final_keys:
            final_keys.append(k)
    if not export_all_keys:
        if selected_keys:
            for k in selected_keys:
                if k not in final_keys:
                    final_keys.append(k)
            final_keys = [k for k in final_keys if k in selected_keys]
        else:
            final_keys = []

    # Optional: Vorschau anzeigen und Export bestätigen lassen (ausgelagert in export_ui.show_preview_dialog)

    if preview_before_export:
        # apply auto-fill rules before showing preview, so users see final export values
        try:
            autofill_band_masses_for_export(leaders, cfg)
        except Exception:
            pass
        # reorder columns for preview according to CSV or alphabetical
        try:
            final_keys = _reorder_final_keys(cfg, final_keys, target_styles)
        except Exception:
            pass
        proceed = ui_show_preview(cfg, leaders, final_keys)
        if not proceed:
            print("[Export] Abgebrochen nach Vorschau.")
            return

    # Zielformat bestimmen
    if mode is None:
        mode = (cfg.get("logging", {}).get("mode") or "csv").lower()
    # Ausgabe-Dateipfade nach Nutzerwunsch bestimmen
    output_path_txt, output_path_stats, output_path_xlsx = get_export_paths(
        mode,
        prompt_user=(picked is None),
        use_standard_override=use_standard_override,
        base_name_override=base_name_override,
    )

    # Optional floor sort for leaders list
    try:
        if cfg.get("export", {}).get("floor_sort", False):
            leaders.sort(key=lambda it: (9999 if it.get("_floor_rank") is None else it.get("_floor_rank"), it.get("text", "")))
    except Exception:
        pass

    # Sicherstellen, dass Auto-Fill auch ohne Vorschau greift
    try:
        autofill_band_masses_for_export(leaders, cfg)
    except Exception:
        pass

    # TXT (wie bisher)
    if mode in ("txt", "csv"):
        write_txt_and_stats(output_path_txt, output_path_stats, export_lines_text, style_counts, target_styles)
        print(f"{len(leaders)} Leader exportiert (TXT):\n{output_path_txt}")
        print(f"Statistik gespeichert in:\n{output_path_stats}")
        return

    # XLSX
    if mode == "xlsx":
        try:
            na_value = cfg.get("export", {}).get("na_value", "NA")

            # reorder final_keys again for the actual export
            try:
                final_keys = _reorder_final_keys(cfg, final_keys, target_styles)
            except Exception:
                pass
            header = ["text", "dimstyle"] + final_keys

            write_xlsx(output_path_xlsx, leaders, [k for k in final_keys], style_counts, target_styles, na_value)
            print(f"{len(leaders)} Leader exportiert (XLSX via xlsxwriter):\n{output_path_xlsx}")
            return

        except Exception as e:
            print("Excel-Export fehlgeschlagen, schreibe TXT stattdessen:", e)
            with open(output_path_txt, "w", encoding="utf-8") as file:
                for line in export_lines_text:
                    file.write(line + "\n")
            return




# Aufruf
# Aufruf; optional: export_leader_texts("xlsx")
export_leader_texts()
