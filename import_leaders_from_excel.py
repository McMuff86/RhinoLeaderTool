#! python 3
# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import os


def load_config():
    try:
        script_dir = os.path.dirname(__file__)
    except Exception:
        script_dir = os.getcwd()
    local_cfg = os.path.join(script_dir, "config.json")
    default = {
        "export": {"na_value": "NA"}
    }
    try:
        import json
        cfg_to_use = local_cfg if os.path.isfile(local_cfg) else None
        if cfg_to_use:
            with open(cfg_to_use, "r", encoding="utf-8") as f:
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


def default_candidate_paths():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    doc_path = sc.doc.Path or ""
    base_dir = os.path.dirname(doc_path) if doc_path else desktop
    doc_name = sc.doc.Name or "leader"
    base_name = os.path.splitext(doc_name)[0] or "leader"
    return [
        os.path.join(base_dir, f"{base_name}_leader_export.xlsx"),
        os.path.join(desktop, f"{base_name}_leader_export.xlsx"),
        os.path.join(base_dir, f"{base_name}_leader_texts.txt"),
    ]


def choose_input_file():
    # Try candidates first
    for p in default_candidate_paths():
        if os.path.isfile(p):
            return p
    # Ask user
    try:
        return rs.OpenFileName("Select leader export file (XLSX or CSV)", "Excel (*.xlsx)|*.xlsx||CSV (*.csv)|*.csv||All (*.*)|*.*||")
    except Exception:
        return None


def read_xlsx(path):
    try:
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.rows)
        if not rows:
            return [], []
        header = [str(c.value) if c.value is not None else "" for c in rows[0]]
        data = []
        for r in rows[1:]:
            data.append([c.value for c in r])
        return header, data
    except Exception as e:
        # Fallback: parse .xlsx via zip (no external deps)
        try:
            modname = getattr(e, "name", "") if hasattr(e, "name") else ""
        except Exception:
            modname = ""
        if isinstance(e, ImportError) or "openpyxl" in str(e) or modname == "openpyxl":
            print("Using built-in XLSX reader (openpyxl not available).")
        else:
            print("Using built-in XLSX reader (openpyxl error):", e)
        return read_xlsx_via_zip(path)


def read_xlsx_via_zip(path):
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(path, 'r') as z:
            # Shared strings
            shared = []
            try:
                with z.open('xl/sharedStrings.xml') as f:
                    ss = ET.parse(f).getroot()
                    # ns handling
                    for si in ss.findall('.//{*}si'):
                        # concatenate all t children
                        text_parts = []
                        for t in si.findall('.//{*}t'):
                            text_parts.append(t.text or '')
                        shared.append(''.join(text_parts))
            except KeyError:
                shared = []

            # First worksheet (xlsxwriter uses sheet1.xml)
            with z.open('xl/worksheets/sheet1.xml') as f:
                ws = ET.parse(f).getroot()

            # Column letter to index
            def col_to_idx(col):
                idx = 0
                for ch in col:
                    if 'A' <= ch <= 'Z':
                        idx = idx * 26 + (ord(ch) - ord('A') + 1)
                return idx - 1  # zero-based

            # Extract rows
            rows = []
            max_cols = 0
            for row in ws.findall('.//{*}row'):
                cells = {}
                for c in row.findall('{*}c'):
                    r = c.get('r') or ''  # e.g., 'B2'
                    # split letters and digits
                    letters = ''.join([ch for ch in r if ch.isalpha()])
                    col_index = col_to_idx(letters) if letters else 0
                    t = c.get('t')  # type
                    v_elem = c.find('{*}v')
                    is_elem = c.find('{*}is')
                    val = ''
                    if t == 's' and v_elem is not None:
                        try:
                            si = int(v_elem.text)
                            val = shared[si] if 0 <= si < len(shared) else ''
                        except Exception:
                            val = ''
                    elif t == 'inlineStr' and is_elem is not None:
                        parts = []
                        for tnode in is_elem.findall('.//{*}t'):
                            parts.append(tnode.text or '')
                        val = ''.join(parts)
                    elif v_elem is not None and v_elem.text is not None:
                        val = v_elem.text
                    else:
                        val = ''
                    cells[col_index] = val
                    if col_index + 1 > max_cols:
                        max_cols = col_index + 1
                # build ordered row
                ordered = [cells.get(i, '') for i in range(max_cols)]
                rows.append(ordered)

            if not rows:
                return [], []
            header = [str(x) if x is not None else '' for x in rows[0]]
            data = []
            for r in rows[1:]:
                data.append([x for x in r])
            return header, data
    except Exception as e:
        print('XLSX zip-parse failed:', e)
        return [], []


def read_csv_generic(path):
    try:
        import csv
        with open(path, "r", encoding="utf-8") as f:
            rdr = csv.reader(f)
            header = next(rdr, [])
            data = [row for row in rdr]
        return header, data
    except Exception as e:
        print("CSV read failed:", e)
        return [], []


def to_string(v):
    try:
        if v is None:
            return ""
        return str(v)
    except Exception:
        return ""


def import_from_table(header, rows, skip_na=True, only_if_changed=True):
    if not header:
        print("No header found. Abort.")
        return
    # Identify standard columns
    name_to_idx = {str(h).strip(): i for i, h in enumerate(header)}
    guid_col = None
    for k in name_to_idx.keys():
        if str(k).strip().lower() == "leaderguid":
            guid_col = name_to_idx[k]
            break
    if guid_col is None:
        print("Column 'LeaderGUID' not found. Cannot map rows to leaders.")
        return

    ignore_cols = set()
    for ign in ["text", "dimstyle"]:
        for k, idx in name_to_idx.items():
            if str(k).strip().lower() == ign:
                ignore_cols.add(idx)

    updated_fields = 0
    touched_leaders = 0

    for row in rows:
        if guid_col >= len(row):
            continue
        guid_str = to_string(row[guid_col]).strip()
        if not guid_str:
            continue
        try:
            import System
            guid = System.Guid(guid_str)
            rhobj = sc.doc.Objects.Find(guid)
        except Exception:
            rhobj = None
        if rhobj is None:
            continue
        leader_id = rhobj.Id
        changed_any = False
        for idx, col_name in enumerate(header):
            if idx == guid_col or idx in ignore_cols:
                continue
            key = str(col_name).strip()
            if key == "":
                continue
            present = idx < len(row)
            if not present:
                continue
            new_val = to_string(row[idx]).strip()
            if skip_na and new_val.upper() == get_na_value(load_config()).upper():
                continue
            old_val = rs.GetUserText(leader_id, key) or ""
            if only_if_changed and old_val == new_val:
                continue
            try:
                rs.SetUserText(leader_id, key, new_val)
                updated_fields += 1
                changed_any = True
            except Exception:
                pass
        if changed_any:
            # ensure LeaderGUID & SchemaVersion remain present
            try:
                if not rs.GetUserText(leader_id, "LeaderGUID"):
                    rs.SetUserText(leader_id, "LeaderGUID", str(leader_id))
                if not rs.GetUserText(leader_id, "SchemaVersion"):
                    rs.SetUserText(leader_id, "SchemaVersion", "1.0")
            except Exception:
                pass
            touched_leaders += 1

    print("Leaders updated:", touched_leaders, "| Fields changed:", updated_fields)


def run():
    cfg = load_config()
    na_value = get_na_value(cfg)

    path = choose_input_file()
    if not path or not os.path.isfile(path):
        print("No file selected.")
        return

    # Options
    skip_na = True
    ans = rs.GetBoolean("Skip NA values when importing?", ("SkipNA", "No", "Yes"), True)
    if ans is not None and len(ans) > 0:
        skip_na = bool(ans[0])
    only_changed = True
    ans2 = rs.GetBoolean("Only update when value changed?", ("OnlyChanged", "No", "Yes"), True)
    if ans2 is not None and len(ans2) > 0:
        only_changed = bool(ans2[0])

    header = []
    rows = []
    if path.lower().endswith(".xlsx"):
        header, rows = read_xlsx(path)
    else:
        header, rows = read_csv_generic(path)
    if not header:
        print("Could not read table header from:", path)
        return

    # Import
    import_from_table(header, rows, skip_na=skip_na, only_if_changed=only_changed)


if __name__ == "__main__":
    run()


