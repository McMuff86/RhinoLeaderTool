#! python 3
# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import Rhino.FileIO as FileIO
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

def load_config():
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
        "aliases": {
            "bbrt": "rahmentuere",
            "bbzt": "zargentuere",
            "bbrtw": "rahmentuere_w",
            "bbst": "schiebetuere",
            "bbsp": "spez"
        }
    }
    try:
        if os.path.isfile(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            for k, v in file_cfg.items():
                default_cfg[k] = v
    except Exception as e:
        print("Konnte config.json nicht laden (verwende Defaults):", e)
    return default_cfg

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
csv_filename = types_cfg[typ]["csv"]

# ✅ Dynamischer Benutzerpfad
user_dir = os.path.expanduser("~")  # ergibt C:\Users\<user>
base_path = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")
csv_path = os.path.join(base_path, csv_filename)

# Ablauf
csv_data = read_csv_attributes(csv_path)
style_id = get_dimstyle_id(dimstyle_name)
if style_id:
    leader_id = create_leader_with_style(style_id)
    if leader_id:
        attach_usertext(leader_id, csv_data)
