#! python 3
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import os
import json
import csv
from datetime import datetime


def load_config():
    user_dir = os.path.expanduser("~")
    base_path = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")
    cfg_path = os.path.join(base_path, "config.json")
    default = {
        "export": {
            "target_styles": [
                "Standard 1:10 Rahmenbeschriftung",
                "Standard 1:10 Rahmenbeschriftung WHG Eingang",
                "Standard 1:10 Zargenbeschriftung",
                "Standard 1:10 Schiebetürbeschriftung",
                "Standard 1:10 Spez.Rahmenbeschriftung"
            ],
            "na_value": "NA"
        }
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


def get_base_path(cfg):
    user_dir = os.path.expanduser("~")
    default_base = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")
    cfg_base = cfg.get("base_path") if isinstance(cfg, dict) else None
    return cfg_base if (cfg_base and os.path.isdir(cfg_base)) else default_base


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
        base_path = get_base_path(cfg)
        types_cfg = (cfg or {}).get("types", {})
        seen = set()
        for _typ, spec in types_cfg.items():
            csv_name = spec.get("csv")
            if not csv_name:
                continue
            csv_path = csv_name if os.path.isabs(csv_name) else os.path.join(base_path, csv_name)
            for key in read_csv_keys(csv_path):
                if key not in seen:
                    seen.add(key)
                    required.append(key)
    except Exception:
        pass
    return required


def migrate_leaders(delete_old_keys=True, write_report=True):
    cfg = load_config()
    target_styles = cfg.get("export", {}).get("target_styles", [])
    na_value = cfg.get("export", {}).get("na_value", "NA")
    # Report-Ziel über Prompt bestimmen
    def choose_report_target(default_filename):
        # Soll ein Report erstellt werden?
        ans = rs.GetBoolean("Create migration report?", ("Report", "No", "Yes"), True)
        if ans is None or not ans[0]:
            return False, None
        # Wohin speichern?
        ans2 = rs.GetBoolean("Save report to Desktop?", ("Desktop", "No", "Yes"), True)
        user_dir = os.path.expanduser("~")
        desktop = os.path.join(user_dir, "Desktop")
        if ans2 is not None and ans2[0]:
            return True, os.path.join(desktop, default_filename)
        # An das Rhino-Dokument anlehnen
        doc_path = sc.doc.Path or ""
        base_dir = os.path.dirname(doc_path) if doc_path else desktop
        report_dir = os.path.join(base_dir, "report")
        if not os.path.isdir(report_dir):
            try:
                os.makedirs(report_dir)
            except Exception:
                report_dir = base_dir
        return True, os.path.join(report_dir, default_filename)

    # Mapping alter → neuer Schlüssel
    key_mapping = {
        "Mauerlichtbreite": "Mauerlichtbreite_plan",
        "Mauerlichthöhe": "Mauerlichthöhe_plan",
        "Mauerstärke": "Mauerstärke_plan",
    }

    # Sicherzustellende neuen Schlüssel (Union aller CSV-Keys aus config.json)
    required_keys = compute_required_keys_from_config(cfg)
    # Zusätzlich hart erforderliche Metadaten-Schlüssel
    for meta_key in ["Haus", "Betriebsauftrag"]:
        if meta_key not in required_keys:
            required_keys.append(meta_key)

    total = 0
    modified = 0
    report_rows = []

    for obj in sc.doc.Objects:
        if isinstance(obj, Rhino.DocObjects.LeaderObject):
            total += 1

            # Filtern nach DimStyle, falls konfiguriert
            process = True
            try:
                dimstyle = sc.doc.DimStyles.FindId(obj.Geometry.DimensionStyleId)
                if target_styles:
                    process = dimstyle is not None and dimstyle.Name in target_styles
            except Exception:
                pass
            if not process:
                continue

            # Bestehende UserText-Werte lesen
            current = {}
            key_store = obj.Attributes.GetUserStrings()
            if key_store:
                for k in key_store.AllKeys:
                    current[k] = key_store[k]

            obj_id = obj.Id
            changed_this = False

            # Mapping anwenden (alte → neue Schlüssel), nur setzen wenn neuer noch nicht existiert
            for old_key, new_key in key_mapping.items():
                if old_key in current:
                    if new_key not in current or (current.get(new_key) is None or current.get(new_key) == ""):
                        rs.SetUserText(obj_id, new_key, current[old_key])
                        changed_this = True
                    if delete_old_keys:
                        rs.SetUserText(obj_id, old_key, None)
                        changed_this = True

            # Fehlende required_keys mit NA auffüllen (nur wenn nicht vorhanden)
            # Dazu aktuellen Stand neu lesen
            key_store = sc.doc.Objects.Find(obj_id).Attributes.GetUserStrings()
            existing_now = set(key_store.AllKeys) if key_store else set()
            for req_key in required_keys:
                if req_key not in existing_now:
                    rs.SetUserText(obj_id, req_key, na_value)
                    changed_this = True

            # LeaderGUID sicherstellen
            existing_guid = rs.GetUserText(obj_id, "LeaderGUID")
            if not existing_guid:
                rs.SetUserText(obj_id, "LeaderGUID", str(obj_id))
                changed_this = True

            # SchemaVersion setzen, falls nicht vorhanden
            existing_schema = rs.GetUserText(obj_id, "SchemaVersion")
            if not existing_schema:
                rs.SetUserText(obj_id, "SchemaVersion", "1.0")
                changed_this = True

            # Reporting sammeln
            if changed_this:
                row = {
                    "LeaderGUID": str(obj_id),
                    "DimStyle": dimstyle.Name if dimstyle else "",
                    "ChangedKeys": ";".join(sorted(list(existing_now.symmetric_difference(set(sc.doc.Objects.Find(obj_id).Attributes.GetUserStrings().AllKeys))))) if key_store else ""
                }
                report_rows.append(row)

            if changed_this:
                modified += 1

    print("Leader-Objekte gesamt:", total)
    print("Davon angepasst:", modified)

    # Report schreiben
    if write_report and report_rows:
        default_name = f"leader_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        should_write, report_path = choose_report_target(default_name)
        if should_write and report_path:
            try:
                with open(report_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["LeaderGUID", "DimStyle", "ChangedKeys"])
                    writer.writeheader()
                    for r in report_rows:
                        writer.writerow(r)
                print("Migrationsreport gespeichert:", report_path)
            except Exception as e:
                print("Konnte Migrationsreport nicht schreiben:", e)


# Bulk-Update: Setzt für alle passenden Leader einen bestimmten UserText-Key auf einen neuen Wert
def bulk_update_key_for_leaders(target_key, new_value, only_if_missing=False, styles=None, write_report=True):
    cfg = load_config()
    target_styles = styles if styles is not None else cfg.get("export", {}).get("target_styles", [])
    # Report-Ziel über Prompt bestimmen
    def choose_report_target(default_filename):
        ans = rs.GetBoolean("Create bulk-update report?", ("Report", "No", "Yes"), True)
        if ans is None or not ans[0]:
            return False, None
        ans2 = rs.GetBoolean("Save report to Desktop?", ("Desktop", "No", "Yes"), True)
        user_dir = os.path.expanduser("~")
        desktop = os.path.join(user_dir, "Desktop")
        if ans2 is not None and ans2[0]:
            return True, os.path.join(desktop, default_filename)
        doc_path = sc.doc.Path or ""
        base_dir = os.path.dirname(doc_path) if doc_path else desktop
        report_dir = os.path.join(base_dir, "report")
        if not os.path.isdir(report_dir):
            try:
                os.makedirs(report_dir)
            except Exception:
                report_dir = base_dir
        return True, os.path.join(report_dir, default_filename)

    total = 0
    touched = 0
    rows = []

    for obj in sc.doc.Objects:
        if isinstance(obj, Rhino.DocObjects.LeaderObject):
            total += 1
            dimstyle = None
            try:
                dimstyle = sc.doc.DimStyles.FindId(obj.Geometry.DimensionStyleId)
            except Exception:
                pass
            # Filtern nach DimStyles, falls konfiguriert
            if target_styles:
                if not dimstyle or dimstyle.Name not in target_styles:
                    continue

            obj_id = obj.Id
            current_store = obj.Attributes.GetUserStrings()
            old_val = None
            if current_store and target_key in current_store.AllKeys:
                old_val = current_store[target_key]

            # Bedingung: nur setzen wenn fehlend
            if only_if_missing and old_val not in (None, ""):
                continue

            rs.SetUserText(obj_id, target_key, new_value)

            # LeaderGUID sicherstellen
            if not rs.GetUserText(obj_id, "LeaderGUID"):
                rs.SetUserText(obj_id, "LeaderGUID", str(obj_id))

            # SchemaVersion, wenn noch nicht vorhanden
            if not rs.GetUserText(obj_id, "SchemaVersion"):
                rs.SetUserText(obj_id, "SchemaVersion", "1.0")

            touched += 1
            rows.append({
                "LeaderGUID": str(obj_id),
                "DimStyle": (dimstyle.Name if dimstyle else ""),
                "Key": target_key,
                "OldValue": (old_val if old_val is not None else ""),
                "NewValue": new_value
            })

    print("Leaders gefunden:", total)
    print("Geänderte Leaders:", touched)

    if write_report and rows:
        default_name = f"leader_bulk_update_{target_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        should_write, report_path = choose_report_target(default_name)
        if should_write and report_path:
            try:
                with open(report_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["LeaderGUID", "DimStyle", "Key", "OldValue", "NewValue"])
                    writer.writeheader()
                    for r in rows:
                        writer.writerow(r)
                print("Bulk-Update-Report gespeichert:", report_path)
            except Exception as e:
                print("Konnte Bulk-Update-Report nicht schreiben:", e)

# Ausführen
if __name__ == "__main__":
    migrate_leaders(delete_old_keys=True, write_report=True)


