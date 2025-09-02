#! python 3
# r: xlsxwriter
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import os
import json
from collections import defaultdict


def load_config():
    user_dir = os.path.expanduser("~")
    base_path = os.path.join(user_dir, "repos", "work", "library", "RhinoLeaderTool")
    cfg_path = os.path.join(base_path, "config.json")
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
    default_base = os.path.join(user_dir, "repos", "work", "library", "RhinoLeaderTool")
    cfg_base = cfg.get("base_path") if isinstance(cfg, dict) else None
    return cfg_base if (cfg_base and os.path.isdir(cfg_base)) else default_base

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

def export_leader_texts(mode=None):
    cfg = load_config()
    # Ziel-Bemaßungsstile
    target_styles = cfg.get("export", {}).get("target_styles", [])
    # Erforderliche Keys aus allen CSV-Dateien (Union)
    required_keys = compute_required_keys_from_config(cfg)

    def get_export_paths(active_mode, prompt_user=True):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        use_standard = True
        if prompt_user:
            # True = Standard (Desktop), False = Dokument-Ordner
            res = rs.GetBoolean("Export to standard Desktop path?", ("StandardPath", "No", "Yes"), True)
            if res is not None and len(res) > 0:
                use_standard = bool(res[0])
        if use_standard:
            base_dir = desktop_path
            base_name = "leader"
        else:
            # Dokumentpfad verwenden
            doc_path = sc.doc.Path or ""
            doc_name = sc.doc.Name or "leader"
            if doc_path:
                base_dir = os.path.dirname(doc_path)
            else:
                # Fallback auf Desktop, wenn Datei ungespeichert
                base_dir = desktop_path
            base_name = os.path.splitext(doc_name)[0] or "leader"

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

                export_lines_text.append(full_line)
                leaders.append({
                    "text": text,
                    "dimstyle": dimstyle.Name,
                    "user": user_dict
                })
                style_name = dimstyle.Name if dimstyle else "Unknown"
                style_counts[style_name] += 1

    # Ausgabe
    if not leaders:
        print("Keine passenden Leader gefunden.")
        return

    # Zielformat bestimmen
    if mode is None:
        mode = (cfg.get("logging", {}).get("mode") or "csv").lower()
    # Ausgabe-Dateipfade nach Nutzerwunsch bestimmen
    output_path_txt, output_path_stats, output_path_xlsx = get_export_paths(mode, prompt_user=True)

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

            # finale Keys: zuerst required, dann zusätzlich gefundene
            final_keys = list(required_keys)
            for k in all_user_keys:
                if k not in final_keys:
                    final_keys.append(k)

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
