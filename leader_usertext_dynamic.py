#! python 3
# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import Rhino.FileIO as FileIO
import Rhino.UI
import scriptcontext as sc
import os
import csv
import sys
import json

def read_csv_attributes(path):
    attributes = {}
    try:
        with open(path, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) == 2:
                    key, value = row
                    attributes[key.strip()] = value.strip()
    except Exception as e:
        print("Fehler beim Lesen der CSV:", e)
    return attributes

def get_dimstyle_id(name):
    dimstyle = sc.doc.DimStyles.FindName(name)
    if dimstyle:
        return dimstyle.Id
    else:
        print(f"Bemaßungsstil '{name}' nicht gefunden.")
        return None

def get_base_path():
    user_dir = os.path.expanduser("~")
    return os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")

def get_selected_csv_folder(cfg, prompt_if_missing=True):
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
            start_dir = (cfg.get("base_path") or get_base_path())
        except Exception:
            start_dir = get_base_path()
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

def find_csv_in_tree(base_dir, csv_name, prompt_user=False, typ=None):
    try:
        if not base_dir or not os.path.isdir(base_dir) or not csv_name:
            return None
        # previously selected mapping
        try:
            section = "RhinoLeaderToolCsvMap"
            map_key = f"{typ}:{csv_name}" if typ else csv_name
            mapped = rs.GetDocumentData(section, map_key)
            if mapped and os.path.isfile(mapped):
                return mapped
        except Exception:
            pass
        direct = os.path.join(base_dir, csv_name)
        if os.path.isfile(direct):
            return direct
        matches = []
        target = os.path.basename(csv_name)
        for root, _dirs, files in os.walk(base_dir):
            for fn in files:
                if fn.lower() == target.lower():
                    matches.append(os.path.join(root, fn))
        if not matches:
            return direct
        if len(matches) == 1:
            chosen = matches[0]
        else:
            rels = [(m, os.path.relpath(m, base_dir)) for m in matches]
            rels.sort(key=lambda x: (len(x[1]), x[1].lower()))
            chosen = rels[0][0]
            if prompt_user:
                try:
                    options = [os.path.relpath(m, base_dir) for m in matches]
                    default_opt = os.path.relpath(chosen, base_dir)
                    sel = rs.ListBox(options, message=f"Multiple CSV matches for {csv_name}. Choose one:", title="Select CSV", default=default_opt)
                    if sel and sel in options:
                        chosen = os.path.join(base_dir, sel)
                except Exception:
                    pass
        try:
            section = "RhinoLeaderToolCsvMap"
            map_key = f"{typ}:{csv_name}" if typ else csv_name
            rs.SetDocumentData(section, map_key, chosen)
        except Exception:
            pass
        return chosen
    except Exception:
        return None

def load_config():
    try:
        script_dir = os.path.dirname(__file__)
    except Exception:
        script_dir = os.getcwd()
    local_cfg = os.path.join(script_dir, "config.json")
    base_path = get_base_path()
    config_path = os.path.join(base_path, "config.json")
    default_cfg = {
        "template_path": "LeaderAnnotationTemplate.3dm",
        "types": {
            "rahmentuere": {"dimstyle": "Standard 1:10 Rahmenbeschriftung", "csv": "rahmentuere.csv"},
            "zargentuere": {"dimstyle": "Standard 1:10 Zargenbeschriftung", "csv": "zargentuere.csv"},
            "schiebetuere": {"dimstyle": "Standard 1:10 Schiebetürbeschriftung", "csv": "schiebetuere.csv"},
            "rahmentuere_w": {"dimstyle": "Standard 1:10 Rahmenbeschriftung WHG Eingang", "csv": "rahmentuerew.csv"},
            "spez": {"dimstyle": "Standard 1:10 Spez.Rahmenbeschriftung", "csv": "spez.csv"}
        },
        "aliases": {}
    }
    try:
        cfg_to_use = local_cfg if os.path.isfile(local_cfg) else (config_path if os.path.isfile(config_path) else None)
        if cfg_to_use:
            with open(cfg_to_use, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            for k, v in file_cfg.items():
                default_cfg[k] = v
    except Exception as e:
        print("Konnte config.json nicht laden (verwende Defaults):", e)
    return default_cfg

def apply_usertext_overrides(cfg, data):
    try:
        overrides = (cfg.get("defaults", {}) or {}).get("usertext_overrides", {}) or {}
        na_value = (cfg.get("export", {}) or {}).get("na_value", "NA")
        for k, v in overrides.items():
            current = data.get(k)
            if current is None or str(current).strip() == "" or str(current).strip().upper() == str(na_value).upper():
                data[k] = v
    except Exception:
        pass

def get_na_value(cfg):
    try:
        return (cfg.get("export", {}) or {}).get("na_value", "NA")
    except Exception:
        return "NA"

def load_saved_globals(cfg):
    saved = {}
    try:
        section = "RhinoLeaderToolGlobals"
        prompt_keys = (cfg.get("defaults", {}) or {}).get("prompt_keys", [])
        for k in prompt_keys:
            try:
                v = rs.GetDocumentData(section, k)
                if v is not None:
                    saved[k] = v
            except Exception:
                pass
    except Exception:
        pass
    return saved

def save_globals(cfg, data):
    try:
        section = "RhinoLeaderToolGlobals"
        for k, v in (data or {}).items():
            try:
                rs.SetDocumentData(section, k, str(v) if v is not None else "")
            except Exception:
                pass
    except Exception:
        pass

def prefill_data_with_saved_globals(cfg, data):
    try:
        saved = load_saved_globals(cfg)
        for k, v in saved.items():
            data[k] = v
    except Exception:
        pass

def merge_globals_into_data(cfg, data, globals_dict):
    try:
        na = get_na_value(cfg)
        for k, v in (globals_dict or {}).items():
            cur = data.get(k)
            if cur is None or str(cur).strip() == "" or str(cur).strip().upper() == str(na).upper():
                data[k] = v
    except Exception:
        pass

def maybe_prompt_for_globals(cfg, data):
    try:
        defaults_cfg = cfg.get("defaults", {}) or {}
        always_prompt = bool(defaults_cfg.get("always_prompt", False))
        prompt_on_first = bool(defaults_cfg.get("prompt_on_first_leader", False))
        if not (always_prompt or prompt_on_first):
            return
        # Prüfen, ob bereits ein Leader vorhanden ist
        any_leader = False
        for obj in sc.doc.Objects:
            try:
                if isinstance(obj.Geometry, Rhino.Geometry.Leader):
                    any_leader = True
                    break
            except Exception:
                continue
        if (any_leader and not always_prompt) and prompt_on_first:
            return
        # Keys per Eto-Dialog abfragen, mit Fallback auf GetString
        prompt_keys = defaults_cfg.get("prompt_keys") or []
        na_value = get_na_value(cfg)
        prefill_data_with_saved_globals(cfg, data)
        try:
            import Eto.Forms as forms
            import Eto.Drawing as drawing

            dialog = forms.Dialog()
            dialog.Title = "Globale Werte setzen"

            layout = forms.DynamicLayout()
            layout.Spacing = drawing.Size(6, 6)
            layout.Padding = drawing.Padding(10)

            textboxes = {}
            for key in prompt_keys:
                lbl = forms.Label()
                lbl.Text = key
                tb = forms.TextBox()
                tb.Text = str(data.get(key, na_value))
                textboxes[key] = tb
                layout.AddRow(lbl, tb)

            ok_btn = forms.Button()
            ok_btn.Text = "OK"
            cancel_btn = forms.Button()
            cancel_btn.Text = "Abbrechen"
            layout.AddSeparateRow(None, ok_btn, cancel_btn)

            def on_ok(sender, e):
                dialog.Tag = True
                dialog.Close()

            def on_cancel(sender, e):
                dialog.Tag = False
                dialog.Close()

            ok_btn.Click += on_ok
            cancel_btn.Click += on_cancel

            dialog.Content = layout
            dialog.Tag = False
            try:
                Rhino.UI.EtoExtensions.ShowSemiModal(dialog, sc.doc, Rhino.UI.RhinoEtoApp.MainWindow)
            except Exception as semimodal_ex:
                print("Hinweis: EtoExtensions.ShowSemiModal fehlgeschlagen:", semimodal_ex)
                dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

            if dialog.Tag:
                for key, tb in textboxes.items():
                    val = (tb.Text or "").strip()
                    if val != "":
                        data[key] = val
            save_globals(cfg, {k: data.get(k, na_value) for k in prompt_keys})
            return
        except Exception as eto_ex:
            print("Eto-Dialog nicht verfügbar, verwende GetString-Fallback. Grund:", eto_ex)
            for k in prompt_keys:
                existing = data.get(k, na_value)
                try:
                    val = rs.GetString(f"Set value for {k} (Enter=keep)", str(existing))
                    if val is not None and val != "":
                        data[k] = val
                except Exception as gs_ex:
                    print("GetString fehlgeschlagen für", k, "Grund:", gs_ex)
            save_globals(cfg, {k: data.get(k, na_value) for k in prompt_keys})
    except Exception:
        pass

def maybe_prompt_for_type_specific(cfg, typ, data):
    try:
        defaults_cfg = cfg.get("defaults", {}) or {}
        keys = list(defaults_cfg.get("type_specific_keys") or [])
        if not keys:
            return
        na_value = get_na_value(cfg)
        section = f"RhinoLeaderToolType:{typ}"
        missing = []
        for k in keys:
            cur = data.get(k, na_value)
            if cur is None or str(cur).strip() == "" or str(cur).strip().upper() == str(na_value).upper():
                saved = rs.GetDocumentData(section, k)
                if saved is not None and saved.strip() != "":
                    data[k] = saved
                else:
                    missing.append(k)
        if not missing:
            return
        try:
            import Eto.Forms as forms
            import Eto.Drawing as drawing
            dialog = forms.Dialog(); dialog.Title = f"{typ}: Werte setzen"
            layout = forms.DynamicLayout(); layout.Spacing = drawing.Size(6, 6); layout.Padding = drawing.Padding(10)
            textboxes = {}
            for key in missing:
                lbl = forms.Label(); lbl.Text = key
                tb = forms.TextBox(); tb.Text = str(data.get(key, na_value))
                textboxes[key] = tb; layout.AddRow(lbl, tb)
            ok_btn = forms.Button(); ok_btn.Text = "OK"
            cancel_btn = forms.Button(); cancel_btn.Text = "Abbrechen"
            layout.AddSeparateRow(None, ok_btn, cancel_btn)
            def on_ok(sender, e): dialog.Tag = True; dialog.Close()
            def on_cancel(sender, e): dialog.Tag = False; dialog.Close()
            ok_btn.Click += on_ok; cancel_btn.Click += on_cancel
            dialog.Content = layout; dialog.Tag = False
            try:
                Rhino.UI.EtoExtensions.ShowSemiModal(dialog, sc.doc, Rhino.UI.RhinoEtoApp.MainWindow)
            except Exception as semimodal_ex:
                print("Hinweis: SemiModal fehlgeschlagen:", semimodal_ex)
                dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
            if dialog.Tag:
                for key, tb in textboxes.items():
                    val = (tb.Text or "").strip()
                    if val != "":
                        data[key] = val
                        rs.SetDocumentData(section, key, val)
            return
        except Exception as eto_ex:
            print("Eto-Dialog nicht verfügbar (type-specific), Fallback:", eto_ex)
            for k in missing:
                existing = data.get(k, na_value)
                try:
                    val = rs.GetString(f"{typ} – {k}", str(existing))
                    if val is not None and val != "":
                        data[k] = val
                        rs.SetDocumentData(section, k, val)
                except Exception as gs_ex:
                    print("GetString fehlgeschlagen für", k, "Grund:", gs_ex)
    except Exception:
        pass

def import_dimstyles_from_template(template_path):
    try:
        if os.path.isfile(template_path):
            model = FileIO.File3dm.Read(template_path)
            if model is None:
                raise Exception("Template konnte nicht gelesen werden.")
            imported_count = 0
            for ds in model.DimStyles:
                if sc.doc.DimStyles.FindName(ds.Name) is None:
                    dup = ds.Duplicate()
                    index = sc.doc.DimStyles.Add(dup)
                    if index is not None and index >= 0:
                        imported_count += 1
            if imported_count > 0:
                print(f"{imported_count} DimStyles aus Template importiert.")
            return True
    except Exception as e:
        print("Fehler beim Import der DimStyles aus Template:", e)
    return False

def create_leader_with_style(dimstyle_id):
    rs.Command("_Leader _Pause _Pause _Pause _Enter", echo=False)
    objs = rs.LastCreatedObjects()
    if not objs:
        print("Kein Leader erstellt.")
        return None

    for obj in objs:
        if rs.ObjectType(obj) == 512:
            rhobj = sc.doc.Objects.Find(obj)
            geo = rhobj.Geometry
            geo.DimensionStyleId = dimstyle_id
            sc.doc.Objects.Replace(obj, geo)
            return obj
    return None

def attach_usertext(obj_id, data):
    for key, value in data.items():
        rs.SetUserText(obj_id, key, value)
    print(f"{len(data)} UserText-Einträge hinzugefügt.")
    try:
        existing = rs.GetUserText(obj_id, "LeaderGUID")
        if existing is None or existing == "":
            rs.SetUserText(obj_id, "LeaderGUID", str(obj_id))
        schema = rs.GetUserText(obj_id, "SchemaVersion")
        if schema is None or schema == "":
            rs.SetUserText(obj_id, "SchemaVersion", "1.0")
    except Exception:
        pass

cfg = load_config()
types_cfg = cfg.get("types", {})
aliases_cfg = cfg.get("aliases", {})

# ✅ Aliasname aus CommandHistory holen
try:
    alias_used = rs.CommandHistory().split("\n")[-2].lower().strip()
    alias_used = alias_used.replace("_", "")  # falls _bbzt verwendet wird
except:
    print("Alias konnte nicht erkannt werden.")
    sys.exit()

if alias_used not in aliases_cfg:
    print(f"Alias '{alias_used}' nicht erkannt.")
    sys.exit()

typ = aliases_cfg[alias_used]
if typ not in types_cfg:
    print(f"Typ '{typ}' nicht in Konfiguration gefunden.")
    sys.exit()

dimstyle_name = types_cfg[typ]["dimstyle"]
# Preset-Auswahl (falls vorhanden)
entry = types_cfg.get(typ, {})
presets = entry.get("presets") or []
csv_filename = entry.get("csv")
preset_name = entry.get("default_preset") or "Standard"
if presets:
    names = [p.get("name") for p in presets if p.get("name")]
    default_name = entry.get("default_preset")
    default_name = default_name if (default_name in names) else (names[0] if names else None)
    try:
        selection = rs.ListBox(names, message=f"Select preset for {typ}", title="Choose Preset", default=default_name)
        chosen_name = selection or default_name
        for p in presets:
            if p.get("name") == chosen_name:
                csv_filename = p.get("csv") or csv_filename
                preset_name = chosen_name or preset_name
                break
    except Exception:
        pass

# ✅ Pfade aus Konfig beziehen (mit Fallback)
user_dir = os.path.expanduser("~")
default_base = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")
csv_base = get_selected_csv_folder(cfg, prompt_if_missing=True) or (cfg.get("base_path") if (cfg.get("base_path") and os.path.isdir(cfg.get("base_path"))) else default_base)
csv_path = find_csv_in_tree(csv_base, csv_filename, prompt_user=True, typ=typ) or os.path.join(csv_base, csv_filename)
template_rel = cfg.get("template_path") or "LeaderAnnotationTemplate.3dm"
template_path = template_rel if os.path.isabs(template_rel) else os.path.join(csv_base, template_rel)

# Ablauf
csv_data = read_csv_attributes(csv_path)
try:
    csv_data["Preset"] = preset_name or "Standard"
except Exception:
    pass
try:
    csv_data["LeaderType"] = typ
except Exception:
    pass
# Erst globalen Prompt (eigenes Buffer dict), dann globale Werte in CSV übernehmen, dann Overrides
globals_buf = {}
maybe_prompt_for_globals(cfg, globals_buf)
saved_globals = load_saved_globals(cfg)
merge_globals_into_data(cfg, csv_data, saved_globals)
# Typ-spezifische Keys (z. B. Betriebsauftrag) erfragen und mergen
type_specific = {}
maybe_prompt_for_type_specific(cfg, typ, type_specific)
merge_globals_into_data(cfg, csv_data, type_specific)
apply_usertext_overrides(cfg, csv_data)
style_id = get_dimstyle_id(dimstyle_name)
if not style_id:
    # Versuche DimStyles aus Template zu importieren
    import_dimstyles_from_template(template_path)
    style_id = get_dimstyle_id(dimstyle_name)
if style_id:
    leader_id = create_leader_with_style(style_id)
    if leader_id:
        attach_usertext(leader_id, csv_data)
