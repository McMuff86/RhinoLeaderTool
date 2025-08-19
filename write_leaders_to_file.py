#! python 3
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import os
import json
from collections import defaultdict

def load_config():
    user_dir = os.path.expanduser("~")
    base_path = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")
    cfg_path = os.path.join(base_path, "config.json")
    default = {
        "logging": {"mode": "csv"},
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

def export_leader_texts(mode=None):
    cfg = load_config()
    # Ziel-Bemaßungsstile
    target_styles = cfg.get("export", {}).get("target_styles", [])
    
    # Ausgabe-Dateipfade vorbereiten
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    output_path_txt = os.path.join(desktop_path, "leader_texts.txt")
    output_path_stats = os.path.join(desktop_path, "leader_stats.txt")
    output_path_xlsx = os.path.join(desktop_path, "leader_export.xlsx")

    # Sammellisten
    export_lines_text = []
    leaders = []  # strukturierte Liste für XLSX
    all_user_keys = []  # Reihenfolge der Keys in der Reihenfolge des ersten Auftretens
    style_counts = defaultdict(int)

    for obj in sc.doc.Objects:
        if isinstance(obj, Rhino.DocObjects.LeaderObject):
            leader = obj.Geometry
            dimstyle_id = leader.DimensionStyleId
            dimstyle = sc.doc.DimStyles.FindId(dimstyle_id)

            if dimstyle and dimstyle.Name in target_styles:
                # Basis-Text
                text = leader.Text.replace('\r\n', ' ').replace('\n', ' ')
                
                # UserText ermitteln (als Dict und Text)
                user_text_pairs = []
                user_dict = {}
                keys = obj.Attributes.GetUserStrings()
                if keys:
                    for key in keys.AllKeys:
                        value = keys[key]
                        user_text_pairs.append(f"{key}={value}")
                        if key not in user_dict:
                            user_dict[key] = value
                        if key not in all_user_keys:
                            all_user_keys.append(key)

                # TXT-Zeile aufbauen
                full_line = text
                if user_text_pairs:
                    full_line += " | " + " | ".join(user_text_pairs)

                export_lines_text.append(full_line)
                leaders.append({
                    "text": text,
                    "dimstyle": dimstyle.Name,
                    "user": user_dict
                })
                style_counts[dimstyle.Name] += 1

    # Ausgabe
    if not leaders:
        print("Keine passenden Leader gefunden.")
        return

    # Zielformat bestimmen
    if mode is None:
        mode = (cfg.get("logging", {}).get("mode") or "csv").lower()

    # TXT (wie bisher)
    if mode in ("txt", "csv"):
        with open(output_path_txt, "w", encoding="utf-8") as file:
            for line in export_lines_text:
                file.write(line + "\n")
        # Statistik
        stats_lines = ["--- Übersicht pro Bemaßungsstil ---"]
        total = 0
        for style in target_styles:
            count = style_counts[style]
            stats_lines.append(f"{style}: {count}")
            total += count
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
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "leaders"
            # Header: text, dimstyle, dann alle Keys
            na_value = cfg.get("export", {}).get("na_value", "NA")
            header = ["text", "dimstyle"] + all_user_keys
            ws.append(header)
            # Rows
            for item in leaders:
                row = [item["text"], item["dimstyle"]]
                user = item["user"]
                for key in all_user_keys:
                    row.append(user.get(key, na_value))
                ws.append(row)

            # Statistik-Blatt
            ws2 = wb.create_sheet("stats")
            ws2.append(["style", "count"])
            total = 0
            for style in target_styles:
                count = style_counts[style]
                ws2.append([style, count])
                total += count
            ws2.append(["Total", total])
            wb.save(output_path_xlsx)
            print(f"{len(leaders)} Leader exportiert (XLSX):\n{output_path_xlsx}")
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
