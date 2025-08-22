#! python 3
# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import Rhino.UI
import scriptcontext as sc
import os
import sys
import json


def get_base_path():
    user_dir = os.path.expanduser("~")
    return os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")


def load_config():
    base_path = get_base_path()
    cfg_path = os.path.join(base_path, "config.json")
    default = {
        "defaults": {
            "prompt_keys": ["Haus", "Betriebsauftragsposition"],
            "type_specific_keys": ["Betriebsauftrag"]
        },
        "export": {"na_value": "NA"}
    }
    try:
        if os.path.isfile(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            for k, v in file_cfg.items():
                default[k] = v
    except Exception:
        pass
    return default


def get_na_value(cfg):
    try:
        return (cfg.get("export", {}) or {}).get("na_value", "NA")
    except Exception:
        return "NA"


def sync_selected_keys(selected_keys, cfg):
    na = get_na_value(cfg)
    defaults_cfg = cfg.get("defaults", {}) or {}
    global_keys = set(defaults_cfg.get("prompt_keys") or [])
    type_keys = set(defaults_cfg.get("type_specific_keys") or [])
    types_cfg = (cfg.get("types") or {})

    updated_fields = 0
    touched_leaders = 0

    for obj in sc.doc.Objects:
        if isinstance(obj, Rhino.DocObjects.LeaderObject):
            leader_id = obj.Id
            # LeaderType lesen oder aus DimStyle ableiten
            leader_type = rs.GetUserText(leader_id, "LeaderType") or ""
            if not leader_type:
                try:
                    dimstyle = sc.doc.DimStyles.FindId(obj.Geometry.DimensionStyleId)
                    if dimstyle:
                        for t, spec in types_cfg.items():
                            if spec.get("dimstyle") == dimstyle.Name:
                                leader_type = t
                                break
                except Exception:
                    pass
            changed_any = False
            for key in selected_keys:
                new_val = None
                try:
                    # Präferenz: Wenn pro Typ ein Wert existiert, diesen bevorzugen, sonst global
                    if leader_type:
                        new_val = rs.GetDocumentData(f"RhinoLeaderToolType:{leader_type}", key)
                    if new_val is None:
                        new_val = rs.GetDocumentData("RhinoLeaderToolGlobals", key)
                except Exception:
                    pass

                if new_val is None:
                    continue
                old_val = rs.GetUserText(leader_id, key)
                if old_val != new_val:
                    rs.SetUserText(leader_id, key, new_val)
                    updated_fields += 1
                    changed_any = True
            if changed_any:
                touched_leaders += 1

    print("Leaders aktualisiert:", touched_leaders, "| Felder geändert:", updated_fields)


def run():
    cfg = load_config()
    defaults_cfg = cfg.get("defaults", {}) or {}
    keys = []
    seen = set()
    for k in (defaults_cfg.get("prompt_keys") or []) + (defaults_cfg.get("type_specific_keys") or []):
        if k not in seen:
            seen.add(k)
            keys.append(k)
    if not keys:
        print("Keine Schlüssel in config.json definiert (defaults.prompt_keys / type_specific_keys).")
        return

    # Eto Mehrfachauswahl (CheckBox je Key)
    try:
        import Eto.Forms as forms
        import Eto.Drawing as drawing

        dialog = forms.Dialog()
        dialog.Title = "Leader Sync – Felder & Werte"
        layout = forms.DynamicLayout()
        layout.Spacing = drawing.Size(6, 6)
        layout.Padding = drawing.Padding(10)

        # Scope-Auswahl: Global oder Grundtyp
        types_cfg = (cfg.get("types") or {})
        scope_names = ["Global"] + [t for t in types_cfg.keys()]
        scope_dd = forms.DropDown()
        for n in scope_names:
            scope_dd.Items.Add(n)
        scope_dd.SelectedIndex = 0
        lbl_scope = forms.Label()
        lbl_scope.Text = "Scope:"
        layout.AddRow(lbl_scope, scope_dd)

        # Helper: Quelle lesen je Scope
        type_keys = set((cfg.get("defaults", {}) or {}).get("type_specific_keys") or [])
        global_keys = set((cfg.get("defaults", {}) or {}).get("prompt_keys") or [])

        def read_source_value(scope_name, key):
            # Global keys werden immer aus Global gelesen
            if key in global_keys:
                return rs.GetDocumentData("RhinoLeaderToolGlobals", key) or ""
            # Typ-spezifische Keys aus Typ lesen, bei Global-Scope leer/auslassen
            if key in type_keys and scope_name != "Global":
                return rs.GetDocumentData(f"RhinoLeaderToolType:{scope_name}", key) or ""
            # Fallback auf Global
            return rs.GetDocumentData("RhinoLeaderToolGlobals", key) or ""

        # Zeilen: Checkbox + Label + TextBox (aktueller Wert editierbar)
        checkboxes = {}
        textboxes = {}
        original_values = {}
        for k in keys:
            cb = forms.CheckBox(); cb.Text = ""
            cb.Checked = k in (defaults_cfg.get("type_specific_keys") or [])
            lbl = forms.Label(); lbl.Text = k
            tb = forms.TextBox();
            val = read_source_value(scope_names[scope_dd.SelectedIndex], k)
            tb.Text = val
            original_values[k] = val
            checkboxes[k] = cb; textboxes[k] = tb
            layout.AddRow(cb, lbl, tb)

        def on_scope_changed(sender, e):
            sel = scope_names[scope_dd.SelectedIndex]
            for k, tb in textboxes.items():
                val2 = read_source_value(sel, k)
                tb.Text = val2
                original_values[k] = val2

        scope_dd.SelectedValueChanged += on_scope_changed

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

        ok_btn.Click += on_ok
        cancel_btn.Click += on_cancel

        dialog.Content = layout
        dialog.Tag = False
        try:
            Rhino.UI.EtoExtensions.ShowSemiModal(dialog, sc.doc, Rhino.UI.RhinoEtoApp.MainWindow)
        except Exception:
            dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

        if not dialog.Tag:
            print("Synchronisation abgebrochen.")
            return

        # Ausgewählt, wenn Checkbox an ODER Text geändert wurde
        selected = []
        for k, cb in checkboxes.items():
            changed = (textboxes[k].Text or "") != (original_values.get(k) or "")
            if bool(cb.Checked) or changed:
                selected.append(k)
        if not selected:
            print("Keine Felder ausgewählt.")
            return
        # Eingetragene Werte in DocData schreiben (je nach Scope)
        sel_scope = scope_names[scope_dd.SelectedIndex]
        for k in keys:
            try:
                val = (textboxes[k].Text or "").strip()
                if k in type_keys:
                    # Typ-spezifische Werte nur schreiben, wenn ein Typ gewählt ist
                    if sel_scope != "Global":
                        section = f"RhinoLeaderToolType:{sel_scope}"
                        rs.SetDocumentData(section, k, val)
                else:
                    # Globale Keys immer global speichern
                    rs.SetDocumentData("RhinoLeaderToolGlobals", k, val)
            except Exception:
                pass
        # Danach synchronisieren
        sync_selected_keys(selected, cfg)
        return
    except Exception as eto_ex:
        print("Eto-Dialog nicht verfügbar, Fallback auf Konsole:", eto_ex)
        # Fallback: einfache Auswahl über Ja/Nein je Key
        selected = []
        for k in keys:
            ans = rs.GetBoolean(f"Sync Feld '{k}'?", ("Ja", "No", "Yes"), False)
            if ans and ans[0]:
                selected.append(k)
        if not selected:
            print("Keine Felder ausgewählt.")
            return
        # Werte via einfache Eingabe setzen
        scope = rs.ListBox(["Global"] + list((cfg.get("types") or {}).keys()), message="Scope wählen", title="Scope", default="Global")
        section = "RhinoLeaderToolGlobals" if scope == "Global" else f"RhinoLeaderToolType:{scope}"
        for k in keys:
            v = rs.GetString(f"Wert für '{k}' setzen (Enter=überspringen)")
            if v is not None and v != "":
                rs.SetDocumentData(section, k, v)
        sync_selected_keys(selected, cfg)


if __name__ == "__main__":
    # Sicherstellen, dass Pfad vorhanden ist, falls in anderem Kontext gestartet
    base = get_base_path()
    if base not in sys.path:
        sys.path.append(base)
    run()


