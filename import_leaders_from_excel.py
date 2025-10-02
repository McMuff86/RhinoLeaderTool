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


def choose_input_file(prompt_always=True, allow_csv=False):
    # Build filter
    if allow_csv:
        filter_str = "Excel (*.xlsx)|*.xlsx||CSV (*.csv)|*.csv||All (*.*)|*.*||"
    else:
        filter_str = "Excel (*.xlsx)|*.xlsx||All (*.*)|*.*||"

    # Compute sensible defaults for dialog
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    doc_path = sc.doc.Path or ""
    base_dir = os.path.dirname(doc_path) if doc_path else desktop
    doc_name = sc.doc.Name or "leader"
    base_name = os.path.splitext(doc_name)[0] or "leader"

    if not prompt_always:
        # Try candidates first
        for p in default_candidate_paths():
            if os.path.isfile(p):
                return p

    # Ask user via dialog
    try:
        # rs.OpenFileName(caption=None, filter=None, folder=None, filename=None, extension=None)
        return rs.OpenFileName(
            "Select leader export file (XLSX)",
            filter_str,
            base_dir,
            f"{base_name}_leader_export.xlsx",
            "xlsx",
        )
    except Exception:
        return None


def read_xlsx(path):
    try:
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb.active
            rows = list(ws.rows)
            if not rows:
                return [], []
            header = [str(c.value) if c.value is not None else "" for c in rows[0]]
            data = []
            for r in rows[1:]:
                data.append([c.value for c in r])
            return header, data
        finally:
            try:
                wb.close()
            except Exception:
                pass
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


def normalize_value_like_old(old_value, new_value, key=None):
    try:
        import re
        old_s = to_string(old_value)
        new_s = to_string(new_value)
        if old_s == "" or new_s == "":
            return new_s

        # Preserve leading zeros for integer-like fields
        int_like_old = re.match(r'^[+-]?\d+$', old_s) is not None
        dec_like_old = re.match(r'^[+-]?\d+\.\d+$', old_s) is not None

        # Special-case known keys
        lk = (key or "").strip().lower()
        if lk in ("betriebsauftrag",):
            # Always zero-pad to previous width if numbers
            if re.match(r'^\d+$', new_s) or re.match(r'^[+-]?\d+(?:\.0+)?$', new_s):
                try:
                    width = len(re.sub(r'^[+-]?', '', old_s))
                    sign = '-' if old_s.startswith('-') else ''
                    n = int(float(new_s))
                    return sign + str(abs(n)).zfill(width)
                except Exception:
                    return new_s
        if lk in ("schemaversion",):
            # Match decimal places from old value if numeric
            if re.match(r'^[+-]?\d+(?:\.\d+)?$', new_s):
                try:
                    decimals = 0
                    if dec_like_old:
                        decimals = len(old_s.split('.')[-1])
                    elif '.' in old_s:
                        decimals = max(1, len(old_s.split('.')[-1]))
                    else:
                        decimals = 1  # ensure at least one decimal as typical schema style like 1.0
                    val = float(new_s)
                    fmt = "{:." + str(decimals) + "f}"
                    return fmt.format(val)
                except Exception:
                    return new_s

        # Generic rules if keys unknown
        if int_like_old:
            # If old had leading zeros, keep width
            try:
                width = len(old_s.lstrip('+').lstrip('-'))
                # detect leading zeros in old
                had_leading_zeros = old_s.lstrip('+').lstrip('-').startswith('0') and width > 1
                if re.match(r'^[+-]?\d+(?:\.0+)?$', new_s):
                    n = int(float(new_s))
                    s = str(abs(n))
                    if had_leading_zeros:
                        s = s.zfill(width)
                    sign = '-' if old_s.startswith('-') else ''
                    return sign + s
            except Exception:
                return new_s
        if dec_like_old and re.match(r'^[+-]?\d+(?:\.\d+)?$', new_s):
            try:
                decimals = len(old_s.split('.')[-1])
                val = float(new_s)
                fmt = "{:." + str(decimals) + "f}"
                return fmt.format(val)
            except Exception:
                return new_s

        return new_s
    except Exception:
        return to_string(new_value)


def import_from_table(header, rows, skip_na=True, only_if_changed=True):
    if not header:
        print("No header found. Abort.")
        return {"touched_leaders": 0, "updated_fields": 0, "changes": []}
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
    changes = []

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
            # normalize new value to preserve formatting like old
            try:
                normalized_new_val = normalize_value_like_old(old_val, new_val, key)
            except Exception:
                normalized_new_val = new_val
            if only_if_changed and old_val == normalized_new_val:
                continue
            try:
                rs.SetUserText(leader_id, key, normalized_new_val)
                updated_fields += 1
                changed_any = True
                try:
                    changes.append({
                        "LeaderGUID": str(leader_id),
                        "Key": key,
                        "OldValue": old_val,
                        "NewValue": normalized_new_val,
                    })
                except Exception:
                    pass
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
    return {"touched_leaders": touched_leaders, "updated_fields": updated_fields, "changes": changes}


def write_diff_csv(changes, source_path):
    try:
        if not changes:
            return None
        import os
        import csv
        from datetime import datetime
        directory = os.path.dirname(source_path)
        base_name = os.path.splitext(os.path.basename(source_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(directory, f"{base_name}_diff_{timestamp}.csv")
        fieldnames = ["LeaderGUID", "Key", "OldValue", "NewValue"]
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rec in changes:
                # ensure all keys exist
                def excel_safe(val):
                    s = "" if val is None else str(val)
                    # Prevent formula injection
                    if s.startswith('='):
                        return "'" + s
                    import re
                    # If numeric-looking, force Excel to treat as text while displaying correctly
                    if re.match(r'^[+-]?\d+(?:\.\d+)?$', s):
                        return '="' + s.replace('"', '""') + '"'
                    return s

                row = {k: excel_safe(rec.get(k, "")) for k in fieldnames}
                writer.writerow(row)
        return out_path
    except Exception as e:
        try:
            print("Failed to write diff CSV:", e)
        except Exception:
            pass
        return None


def run():
    cfg = load_config()
    na_value = get_na_value(cfg)

    path = choose_input_file(prompt_always=True, allow_csv=False)
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

    # Import and collect changes
    result = import_from_table(header, rows, skip_na=skip_na, only_if_changed=only_changed)
    try:
        changes = (result or {}).get("changes", [])
    except Exception:
        changes = []
    diff_path = write_diff_csv(changes, path)
    if diff_path:
        print("Diff written:", diff_path)
    else:
        print("No changes to write or failed to write diff file.")


if __name__ == "__main__":
    run()


