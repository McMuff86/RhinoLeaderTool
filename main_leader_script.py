#! python 3
# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import Rhino.FileIO as FileIO
import scriptcontext as sc
import os
import csv
import json
from datetime import datetime

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

def get_base_path():
    user_dir = os.path.expanduser("~")
    return os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")

def load_config():
    base_path = get_base_path()
    config_path = os.path.join(base_path, "config.json")
    default_config = {
        "base_path": base_path,
        "template_path": "LeaderAnnotationTemplate.3dm",
        "logging": {
            "mode": "csv",  # csv | xlsx
            "file": "created_leaders_log.csv"
        },
        "types": {
            "rahmentuere": {"dimstyle": "Standard 1:10 Rahmenbeschriftung", "csv": "rahmentuere.csv"},
            "zargentuere": {"dimstyle": "Standard 1:10 Zargenbeschriftung", "csv": "zargentuere.csv"},
            "schiebetuere": {"dimstyle": "Standard 1:10 Schiebetürbeschriftung", "csv": "schiebetuere.csv"},
            "rahmentuere_w": {"dimstyle": "Standard 1:10 Rahmenbeschriftung WHG Eingang", "csv": "rahmentuerew.csv"},
            "spez": {"dimstyle": "Standard 1:10 Spez.Rahmenbeschriftung", "csv": "spez.csv"}
        }
    }

    try:
        if os.path.isfile(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            # flach mergen (Datei-Werte überschreiben Default)
            for k, v in file_cfg.items():
                default_config[k] = v
    except Exception as e:
        print("Konnte config.json nicht laden (verwende Defaults):", e)
    return default_config

def get_dimstyle_id(name):
    dimstyle = sc.doc.DimStyles.FindName(name)
    if dimstyle:
        return dimstyle.Id
    else:
        print(f"Bemaßungsstil '{name}' nicht gefunden.")
        return None

def import_dimstyles_from_template(template_path):
    try:
        if os.path.isfile(template_path):
            model = FileIO.File3dm.Read(template_path)
            if model is None:
                raise Exception("Template konnte nicht gelesen werden.")
            imported_count = 0
            for ds in model.DimStyles:
                if sc.doc.DimStyles.FindName(ds.Name) is None:
                    # Kopie anlegen und hinzufügen
                    dup = ds.Duplicate()
                    index = sc.doc.DimStyles.Add(dup)
                    if index is not None and index >= 0:
                        imported_count += 1
            if imported_count > 0:
                print(f"{imported_count} DimStyles aus Template importiert.")
            return True
        else:
            print("Template-Datei nicht gefunden:", template_path)
    except Exception as e:
        print("Fehler beim Import der DimStyles aus Template:", e)
    return False

def ensure_dimstyle_exists(dimstyle_name, template_full_path):
    dim_id = get_dimstyle_id(dimstyle_name)
    if dim_id:
        return dim_id
    # Versuch, aus Template zu importieren
    if import_dimstyles_from_template(template_full_path):
        dim_id = get_dimstyle_id(dimstyle_name)
        if dim_id:
            return dim_id
    return None

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
        # Persistente Zuordnung: LeaderGUID als UserText speichern
        existing = rs.GetUserText(obj_id, "LeaderGUID")
        if existing is None or existing == "":
            rs.SetUserText(obj_id, "LeaderGUID", str(obj_id))
        # Schema-Version setzen, falls nicht vorhanden
        schema = rs.GetUserText(obj_id, "SchemaVersion")
        if schema is None or schema == "":
            rs.SetUserText(obj_id, "SchemaVersion", "1.0")
    except Exception:
        pass

def log_leader_creation(cfg, leader_id, typ, dimstyle_name, csv_filename):
    try:
        log_cfg = cfg.get("logging", {})
        mode = (log_cfg.get("mode") or "csv").lower()
        cfg_base = cfg.get("base_path")
        base_path = cfg_base if (cfg_base and os.path.isdir(cfg_base)) else get_base_path()
        log_file = log_cfg.get("file") or ("created_leaders_log.csv" if mode == "csv" else "created_leaders_log.xlsx")
        # Korrigiere Dateiendung, falls XLSX-Modus mit unpassender Endung
        if mode == "xlsx" and not log_file.lower().endswith((".xlsx", ".xlsm")):
            root, _ = os.path.splitext(log_file)
            log_file = root + ".xlsx"
        log_path = os.path.join(base_path, log_file)

        timestamp = datetime.now().isoformat(timespec="seconds")
        doc_name = sc.doc.Name or "Untitled"
        leader_str = str(leader_id)

        if mode == "xlsx":
            try:
                from openpyxl import Workbook, load_workbook
                if os.path.exists(log_path):
                    wb = load_workbook(log_path)
                    ws = wb.active
                else:
                    wb = Workbook()
                    ws = wb.active
                    ws.append(["timestamp", "document", "leader_guid", "type", "dimstyle", "csv"])
                ws.append([timestamp, doc_name, leader_str, typ, dimstyle_name, csv_filename])
                wb.save(log_path)
                return
            except Exception as e:
                print("Excel-Logging nicht verfügbar, fallback zu CSV:", e)
                mode = "csv"

        # CSV (Default/Fallback)
        import io
        header_needed = not os.path.exists(log_path)
        with io.open(log_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if header_needed:
                writer.writerow(["timestamp", "document", "leader_guid", "type", "dimstyle", "csv"])
            writer.writerow([timestamp, doc_name, leader_str, typ, dimstyle_name, csv_filename])
    except Exception as e:
        print("Fehler beim Logging der Leader-Erstellung:", e)

def run_leader_for_type(typ):
    cfg = load_config()
    types_cfg = cfg.get("types", {})
    if typ not in types_cfg:
        print(f"Typ '{typ}' nicht erkannt.")
        return

    dimstyle_name = types_cfg[typ]["dimstyle"]
    csv_filename = types_cfg[typ]["csv"]

    cfg_base = cfg.get("base_path")
    base_path = cfg_base if (cfg_base and os.path.isdir(cfg_base)) else get_base_path()
    csv_path = os.path.join(base_path, csv_filename)
    template_rel = cfg.get("template_path") or "LeaderAnnotationTemplate.3dm"
    template_path = template_rel if os.path.isabs(template_rel) else os.path.join(base_path, template_rel)

    csv_data = read_csv_attributes(csv_path)
    style_id = ensure_dimstyle_exists(dimstyle_name, template_path)
    if style_id:
        leader_id = create_leader_with_style(style_id)
        if leader_id:
            attach_usertext(leader_id, csv_data)
            log_leader_creation(cfg, leader_id, typ, dimstyle_name, csv_filename)
