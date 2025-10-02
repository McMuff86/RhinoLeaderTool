#! python 3
# r: xlsxwriter
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import Rhino.UI
import os
import json
import re
from collections import defaultdict


def load_config():
    """Load configuration with robust repo-relative discovery.

    Search order for config.json:
      1) RHINOLEADERTOOL_CONFIG env var (absolute file path)
      2) Next to this script (__file__)
      3) Current working directory
      4) Legacy default under ~/source/repos/work/library/RhinoLeaderTool/config.json

    Also ensure a sensible base_path exists (defaults to the script directory
    when not explicitly provided), so other functions can locate CSVs and
    preset files within the cloned repository.
    """
    user_dir = os.path.expanduser("~")
    legacy_base = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")
    script_dir = os.path.dirname(os.path.abspath(__file__))

    candidates = []
    try:
        env_path = os.environ.get("RHINOLEADERTOOL_CONFIG")
        if env_path:
            candidates.append(env_path)
    except Exception:
        pass
    candidates.append(os.path.join(script_dir, "config.json"))
    candidates.append(os.path.join(os.getcwd(), "config.json"))
    candidates.append(os.path.join(legacy_base, "config.json"))

    cfg_path = None
    for path in candidates:
        try:
            if path and os.path.isfile(path):
                cfg_path = path
                break
        except Exception:
            continue

    default = {
        "logging": {"mode": "xlsx"},
        "export": {
            "target_styles": [
                "Standard 1:10 Rahmenbeschriftung",
                "Standard 1:10 Rahmenbeschriftung WHG Eingang",
                "Standard 1:10 Zargenbeschriftung",
                "Standard 1:10 Schiebetürbeschriftung",
                "Standard 1:10 Spez.Rahmenbeschriftung"
            ],
            "na_value": "NA",
            "floor_sort": True
        }
    }

    try:
        if cfg_path:
            with open(cfg_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            for k, v in file_cfg.items():
                default[k] = v
    except Exception:
        pass

    # Guarantee a valid base_path pointing to the repository when possible
    try:
        if not default.get("base_path"):
            default["base_path"] = script_dir
    except Exception:
        pass
    return default

def get_base_path(cfg):
    user_dir = os.path.expanduser("~")
    default_base = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")
    cfg_base = cfg.get("base_path") if isinstance(cfg, dict) else None
    if cfg_base and os.path.isdir(cfg_base):
        return cfg_base
    # Prefer repository directory (where this script lives) if present
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(script_dir):
            return script_dir
    except Exception:
        pass
    return default_base

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
            csv_name = spec.get("csv")
            if not csv_name:
                continue
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
    return required

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
        rb_doc = forms.RadioButton(); rb_doc.Text = "Ordner der 3dm-Datei"
        rb_desktop.Checked = True
        # Gruppieren: nur rb_doc an rb_desktop anhängen
        try:
            rb_doc.Group = rb_desktop
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
        # Spalten aufteilen
        mid = (len(sorted_keys) + 1) // 2
        left_keys = sorted_keys[:mid]
        right_keys = sorted_keys[mid:]
        col_left = forms.DynamicLayout(); col_left.Spacing = drawing.Size(4, 4)
        col_right = forms.DynamicLayout(); col_right.Spacing = drawing.Size(4, 4)
        for k in left_keys:
            cbk = forms.CheckBox(); cbk.Text = k; cbk.Checked = True
            key_cbx[k] = cbk
            col_left.AddRow(cbk)
        for k in right_keys:
            cbk = forms.CheckBox(); cbk.Text = k; cbk.Checked = True
            key_cbx[k] = cbk
            col_right.AddRow(cbk)
        cols_container = forms.DynamicLayout(); cols_container.Spacing = drawing.Size(12, 6)
        cols_container.AddRow(col_left, col_right)
        scroll = forms.Scrollable(); scroll.Content = cols_container
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

    # Optional: Vorschau anzeigen und Export bestätigen lassen
    def show_preview_dialog(cfg, leaders, final_keys):
        try:
            import Eto.Forms as forms
            import Eto.Drawing as drawing

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

            # 1) Stabile Listenansicht (kompakt)
            try:
                list_page = forms.TabPage()
                list_page.Text = "Liste"
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
                # Filterfunktion für Liste
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
                # Scrollable für Liste
                try:
                    list_scroll = forms.Scrollable()
                    list_scroll.Content = listbox
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

            # 2) Tabellenansicht (Beta) – robust gebaut, kann fehlschlagen ohne Crash
            grid = None
            try:
                grid_page = forms.TabPage(); grid_page.Text = "Tabelle"
                # TreeGridView mit expliziten TreeGridItem-Objekten (Rhino8/Python3 stabil)
                grid = forms.TreeGridView()
                grid.ShowHeader = True
                grid.AllowMultipleSelection = False
                grid.Height = 420
                try:
                    grid.RowHeight = 22
                except Exception:
                    pass

                # Abbildung Spalte -> Feldname ohne Tag nutzen (robuster für ältere Eto-Versionen)
                try:
                    # Sichtdaten (werden durch Suche gefiltert)
                    row_data = list(rows)
                    row_view_ref = {"data": row_data}

                    # Spalten und Schlüssel in definierter Reihenfolge
                    col_keys = ["text", "dimstyle"]
                    def add_col(idx, name, width=None):
                        col = forms.GridColumn()
                        col.HeaderText = name
                        try:
                            if width:
                                col.Width = width
                        except Exception:
                            pass
                        # Editable nur für UserText-Keys (nicht für text/dimstyle/LeaderGUID)
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
                    # ensure LeaderGUID column exists (hidden) to enable 'Element anzeigen'
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
                            # Hard fallback: build a simple collection-like object
                            class _SimpleStore(list):
                                pass
                            items = _SimpleStore()
                        for r in data_rows:
                            try:
                                vals = ["" if r.get(k) is None else str(r.get(k)) for k in col_keys]
                            except Exception:
                                vals = ["" for _ in col_keys]
                            try:
                                it = forms.TreeGridItem(vals)
                            except Exception:
                                it = forms.TreeGridItem()
                                it.Values = vals
                            try:
                                items.Add(it)
                            except Exception:
                                items.append(it)
                        return items

                    # Sortierung per Spaltenkopf
                    sort_state = {"key": None, "desc": False}
                    def on_header_click(sender, e):
                        try:
                            # Spaltenindex ermitteln
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
                            # Toggle Richtung
                            if sort_state.get("key") == key:
                                sort_state["desc"] = not bool(sort_state.get("desc", False))
                            else:
                                sort_state["key"] = key
                                sort_state["desc"] = False

                            data = list(row_view_ref.get("data") or [])
                            def make_sort_tuple(val):
                                try:
                                    if val is None:
                                        return (2, "")
                                    s = str(val).strip()
                                    # numerisch versuchen
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
                    # Für TreeGridView existiert kein ColumnHeaderClick-Event in allen Builds; ersatzweise
                    # klicken wir auf die Headers über Grid.Columns[i].HeaderClick, falls verfügbar.
                    wired = False
                    try:
                        grid.ColumnHeaderClick += on_header_click
                        wired = True
                    except Exception:
                        wired = False
                    if not wired:
                        try:
                            for c in grid.Columns:
                                try:
                                    c.HeaderClick += on_header_click
                                    wired = True
                                except Exception:
                                    pass
                        except Exception:
                            pass

                    # Unterschiede zwischen sichtbaren Zellenwerten und Baseline zählen
                    def update_change_counter():
                        try:
                            # Index der GUID-Spalte ermitteln
                            try:
                                guid_idx = col_keys.index("LeaderGUID")
                            except Exception:
                                guid_idx = -1
                            if guid_idx < 0:
                                return
                            # DataStore lesen
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

                    # Start der Bearbeitung: schütze schreibgeschützte Spalten
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

                    # Zellenbearbeitung → in Rhino-Objekt (UserText) und lokale Daten zurückschreiben
                    def on_cell_edited(sender, e):
                        try:
                            # Spaltenindex bestimmen
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
                            # nicht editierbare Felder ignorieren
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
                                # Fallback über Textspalte → Baseline suchen
                                try:
                                    t_idx = col_keys.index("text")
                                    row_txt = vals[t_idx] if t_idx < len(vals) else None
                                    if row_txt:
                                        for r in (row_view_ref.get("data") or []):
                                            if r.get("text") == row_txt and r.get("_guid"):
                                                guid_text = r.get("_guid"); break
                                except Exception:
                                    guid_text = None
                            if not guid_text:
                                return
                            # pending Merker; tatsächliches Schreiben via Commit-Button
                            add_pending(guid_text, key, new_val)
                            try:
                                # Schreibe explizit wieder in die Item-Values, falls der Editor nicht committed hat
                                e.Item.Values = vals
                            except Exception:
                                pass
                            try:
                                update_change_counter()
                            except Exception:
                                pass
                            # Baseline nicht sofort verändern (damit Commit Unterschiede erkennt)
                        except Exception:
                            pass
                    try:
                        grid.CellEdited += on_cell_edited
                    except Exception:
                        pass

                    # Alternativ: Doppelklick öffnet kleines Eingabefeld zur Bearbeitung
                    def prompt_value(title, initial):
                        try:
                            import Eto.Forms as forms
                            import Eto.Drawing as drawing
                            dlg = forms.Dialog()
                            dlg.Title = title
                            layout = forms.DynamicLayout(); layout.Padding = drawing.Padding(10); layout.Spacing = drawing.Size(6,6)
                            tb = forms.TextBox(); tb.Text = "" if initial is None else str(initial)
                            layout.AddRow(tb)
                            okb = forms.Button(); okb.Text = "OK"
                            cb = forms.Button(); cb.Text = "Abbrechen"
                            def _ok(s,ev): dlg.Tag = tb.Text; dlg.Close()
                            def _cb(s,ev): dlg.Tag = None; dlg.Close()
                            okb.Click += _ok; cb.Click += _cb
                            layout.AddSeparateRow(None, okb, cb)
                            dlg.Content = layout; dlg.Tag = None
                            try:
                                dlg.ShowModal()
                            except Exception:
                                try:
                                    Rhino.UI.EtoExtensions.ShowSemiModal(dlg, sc.doc, Rhino.UI.RhinoEtoApp.MainWindow)
                                except Exception:
                                    dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
                            return dlg.Tag
                        except Exception:
                            return None

                    def on_cell_double(sender, e):
                        try:
                            r = e.Row; col = e.Column
                            if r is None or col is None:
                                return
                            # Spaltenindex und Key
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
                            current = vals[col_index] if col_index < len(vals) else ""
                            new_val = prompt_value("Wert bearbeiten", current)
                            if new_val is None:
                                return
                            # schreibe in UI-Item (damit Commit-Vergleich greift)
                            try:
                                if col_index < len(vals):
                                    vals[col_index] = new_val
                                else:
                                    return
                            except Exception:
                                pass
                            # GUID holen
                            guid_text = None
                            try:
                                gidx = col_keys.index("LeaderGUID")
                                if gidx < len(vals):
                                    guid_text = vals[gidx]
                            except Exception:
                                guid_text = None
                            if not guid_text:
                                # Fallback über Textspalte → Baseline suchen
                                try:
                                    t_idx = col_keys.index("text")
                                    row_txt = vals[t_idx] if t_idx < len(vals) else None
                                    if row_txt:
                                        for r in (row_view_ref.get("data") or []):
                                            if r.get("text") == row_txt and r.get("_guid"):
                                                guid_text = r.get("_guid"); break
                                except Exception:
                                    guid_text = None
                            if guid_text:
                                add_pending(guid_text, key, new_val)
                                update_change_counter()
                        except Exception:
                            pass
                    # Binde Doppelklick-Event
                    bound = False
                    try:
                        grid.CellDoubleClick += on_cell_double
                        bound = True
                    except Exception:
                        bound = False
                    if not bound:
                        try:
                            grid.DoubleClick += on_cell_double
                        except Exception:
                            pass

                    def apply_filter_grid():
                        try:
                            s = (search_tb.Text or "").strip().lower()
                            if not s:
                                row_view_ref["data"] = row_data
                                grid.DataStore = build_store(row_view_ref["data"])
                                return
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
                        except Exception as _ex:
                            row_view_ref["data"] = row_data
                            grid.DataStore = build_store(row_view_ref["data"])
                    search_tb.TextChanged += lambda s, e: apply_filter_grid()
                    # Erste Füllung: vollständige Daten zuweisen
                    row_view_ref["data"] = row_data
                    grid.DataStore = build_store(row_view_ref["data"])

                except Exception as grid_build_ex:
                    print("[Preview] Tabellen-Setup fehlgeschlagen:", grid_build_ex)

                # Scrollable für Tabelle
                try:
                    grid_scroll = forms.Scrollable()
                    grid_scroll.Content = grid
                    grid_scroll.ExpandContentWidth = True
                    grid_scroll.ExpandContentHeight = False
                    grid_page.Content = grid_scroll
                except Exception:
                    grid_page.Content = grid
                tabs.Pages.Add(grid_page)
            except Exception as grid_ex:
                print("[Preview] Tabellenansicht deaktiviert:", grid_ex)

            count_lbl = forms.Label();
            try:
                count_lbl.Text = "{} Leader in der Vorschau".format(len(leaders))
            except Exception:
                count_lbl.Text = "{} Leader in der Vorschau".format(len(leaders))
            layout.AddRow(count_lbl)

            # Content in Scrollable, Buttons bleiben sichtbar
            try:
                scroll = forms.Scrollable()
                scroll.Content = content_panel
                scroll.ExpandContentWidth = True
                scroll.ExpandContentHeight = False
                layout.AddRow(scroll)
            except Exception:
                layout.AddRow(content_panel)

            btn_export = forms.Button(); btn_export.Text = "Exportieren"
            btn_cancel = forms.Button(); btn_cancel.Text = "Abbrechen"
            btn_show = forms.Button(); btn_show.Text = "Element anzeigen"
            btn_commit = forms.Button(); btn_commit.Text = "Commit Changes"
            pending_count_lbl = forms.Label(); pending_count_lbl.Text = "Änderungen: 0"
            # Periodischer Refresh des Änderungscounters (falls Edit-Events nicht feuern)
            try:
                import Eto.Forms as forms
                changes_timer = forms.UITimer()
                try:
                    changes_timer.Interval = 0.5
                except Exception:
                    pass
                def _tick(s, e):
                    try:
                        update_change_counter()
                    except Exception:
                        pass
                changes_timer.Elapsed += _tick
                try:
                    changes_timer.Start()
                except Exception:
                    pass
            except Exception:
                pass
            def on_export(sender, e):
                dialog.Tag = True
                dialog.Close()
            def on_cancel(sender, e):
                dialog.Tag = False
                dialog.Close()
            def on_show(sender, e):
                try:
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
                    # read guid from hidden column when possible
                    if vals is not None:
                        try:
                            gidx = col_keys.index("LeaderGUID")
                            if gidx < len(vals):
                                guid_text = vals[gidx]
                        except Exception:
                            guid_text = None
                    # Fallback via current view rows matching text
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
                            rs.SelectObject(guid_obj)
                            rs.ZoomSelected()
                        except Exception:
                            pass
                except Exception:
                    pass
            btn_export.Click += on_export; btn_cancel.Click += on_cancel
            try:
                btn_show.Click += on_show
            except Exception:
                pass
            def on_commit(sender, e):
                try:
                    total = 0
                    # 1) Änderungen aus DataStore direkt ermitteln (robust, unabhängig von Edit-Events)
                    try:
                        gidx = col_keys.index("LeaderGUID")
                    except Exception:
                        gidx = -1
                    try:
                        ds = grid.DataStore
                    except Exception:
                        ds = None
                    if ds is not None and gidx >= 0:
                        try:
                            import System
                            for it in ds:
                                try:
                                    vals = it.Values
                                except Exception:
                                    vals = None
                                if vals is None or gidx >= len(vals):
                                    continue
                                gtxt = vals[gidx]
                                if not gtxt:
                                    continue
                                try:
                                    obj_id = System.Guid(gtxt)
                                except Exception:
                                    obj_id = None
                                if obj_id is None:
                                    continue
                                # Vergleiche alle editierbaren Spalten
                                for c_index, key in enumerate(col_keys):
                                    if key in ("text", "dimstyle", "LeaderGUID"):
                                        continue
                                    new_val = vals[c_index] if c_index < len(vals) else ""
                                    old_val = None
                                    try:
                                        row = guid_to_row.get(gtxt)
                                        if row is not None:
                                            old_val = row.get(key, "")
                                    except Exception:
                                        old_val = None
                                    if str(new_val) != str(old_val):
                                        try:
                                            rs.SetUserText(obj_id, key, "" if new_val is None else str(new_val))
                                            total += 1
                                        except Exception:
                                            pass
                                        try:
                                            if row is not None:
                                                row[key] = "" if new_val is None else str(new_val)
                                        except Exception:
                                            pass
                                        try:
                                            li = guid_to_leader.get(gtxt)
                                            if li is not None:
                                                li.get("user", {})[key] = "" if new_val is None else str(new_val)
                                        except Exception:
                                            pass
                        except Exception:
                            pass
                    # 2) Zusätzlich noch event-basierte pending_changes abarbeiten (falls vorhanden)
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
                                rs.SetUserText(obj_id, k, v)
                                total += 1
                            except Exception:
                                pass
                    # Clear nach Commit
                    pending_changes.clear()
                    try:
                        pending_count_lbl.Text = "Änderungen: 0"
                    except Exception:
                        pass
                    try:
                        print("[Preview] Commit: {} Werte in UserText geschrieben.".format(total))
                    except Exception:
                        pass
                except Exception:
                    pass
            try:
                btn_commit.Click += on_commit
            except Exception:
                pass
            layout.AddSeparateRow(None, pending_count_lbl, btn_show, btn_commit, btn_export, btn_cancel)

            dialog.Content = layout
            dialog.Tag = False
            # Stabil: erst SemiModal versuchen, dann Modal als Fallback
            try:
                Rhino.UI.EtoExtensions.ShowSemiModal(dialog, sc.doc, Rhino.UI.RhinoEtoApp.MainWindow)
            except Exception:
                try:
                    dialog.ShowModal()
                except Exception:
                    try:
                        dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
                    except Exception:
                        return True
            return bool(dialog.Tag)
        except Exception as e:
            print("[Preview] Fehler beim Aufbau der Vorschau:", e)
            return True

    if preview_before_export:
        proceed = show_preview_dialog(cfg, leaders, final_keys)
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

    # TXT (wie bisher)
    if mode in ("txt", "csv"):
        with open(output_path_txt, "w", encoding="utf-8") as file:
            for line in export_lines_text:
                file.write(line + "\n")
        # Statistik
        stats_lines = ["--- Übersicht pro Bemaßungsstil ---"]
        # Gesamtsumme über alle gezählten Stile
        total = sum(style_counts.values())
        if target_styles:
            # zuerst die konfigurierten Stile in der gewünschten Reihenfolge
            for style in target_styles:
                count = style_counts.get(style, 0)
            stats_lines.append(f"{style}: {count}")
            # anschließend alle übrigen Stile alphabetisch
            extra_styles = [s for s in style_counts.keys() if s not in target_styles]
            for style in sorted(extra_styles):
                stats_lines.append(f"{style}: {style_counts[style]}")
        else:
            for style in sorted(style_counts.keys()):
                stats_lines.append(f"{style}: {style_counts[style]}")
        stats_lines.append(f"Total: {total} Leader")
        with open(output_path_stats, "w", encoding="utf-8") as stats_file:
            for line in stats_lines:
                stats_file.write(line + "\n")
        print(f"{len(leaders)} Leader exportiert (TXT):\n{output_path_txt}")
        print(f"Statistik gespeichert in:\n{output_path_stats}")
        return

    # XLSX
    if mode == "xlsx":
        try:
            import xlsxwriter

            na_value = cfg.get("export", {}).get("na_value", "NA")

            header = ["text", "dimstyle"] + final_keys

            workbook = xlsxwriter.Workbook(output_path_xlsx)
            ws = workbook.add_worksheet("leaders")

            # Header
            for c, name in enumerate(header):
                ws.write(0, c, name)

            # Datenzeilen + CSV-Mirror vorbereiten
            row_idx = 1
            csv_rows = []
            csv_rows.append(header)
            for item in leaders:
                row_vals = [item["text"], item["dimstyle"]]
                user = item["user"]
                for key in final_keys:
                    row_vals.append(normalize_value_for_excel(user.get(key, na_value), na_value))
                for c, val in enumerate(row_vals):
                    ws.write(row_idx, c, val)
                csv_rows.append([str(v) if v is not None else "" for v in row_vals])
                row_idx += 1

            # Stats-Sheet
            ws2 = workbook.add_worksheet("stats")
            ws2.write(0, 0, "style")
            ws2.write(0, 1, "count")
            r = 1
            total = sum(style_counts.values())
            if target_styles:
                for style in target_styles:
                    ws2.write(r, 0, style); ws2.write(r, 1, style_counts.get(style, 0)); r += 1
                extra = [s for s in style_counts.keys() if s not in target_styles]
                for style in sorted(extra):
                    ws2.write(r, 0, style); ws2.write(r, 1, style_counts[style]); r += 1
            else:
                for style in sorted(style_counts.keys()):
                    ws2.write(r, 0, style); ws2.write(r, 1, style_counts[style]); r += 1
            ws2.write(r, 0, "Total"); ws2.write(r, 1, total)

            workbook.close()
            # CSV-Mirror neben der XLSX schreiben (für Import ohne openpyxl)
            try:
                csv_path = os.path.splitext(output_path_xlsx)[0] + ".csv"
                import io, csv as _csv
                with io.open(csv_path, "w", encoding="utf-8", newline="") as f:
                    writer = _csv.writer(f)
                    for row in csv_rows:
                        writer.writerow(row)
            except Exception:
                pass
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
