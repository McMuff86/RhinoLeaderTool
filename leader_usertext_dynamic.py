#! python 3
# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
import os
import csv
import sys

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

# 💡 Mapping Aliasname → Stilname und CSV-Datei
mapping = {
    "bbrt": ("Standard 1:10 Rahmenbeschriftung", "rahmentuere.csv"),
    "bbzt": ("Standard 1:10 Zargenbeschriftung", "zargentuere.csv"),
    "bbst": ("Standard 1:10 Schiebetürbeschriftung", "schiebetuere.csv")
}

# ✅ Aliasname aus CommandHistory holen
try:
    alias_used = rs.CommandHistory().split("\n")[-2].lower().strip()
    alias_used = alias_used.replace("_", "")  # falls _bbzt verwendet wird
except:
    print("Alias konnte nicht erkannt werden.")
    sys.exit()

if alias_used not in mapping:
    print(f"Alias '{alias_used}' nicht erkannt.")
    sys.exit()

dimstyle_name, csv_filename = mapping[alias_used]

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
