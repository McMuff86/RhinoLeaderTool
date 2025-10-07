import os


def write_txt_and_stats(output_path_txt, output_path_stats, export_lines_text, style_counts, target_styles):
    with open(output_path_txt, "w", encoding="utf-8") as file:
        for line in export_lines_text:
            file.write(line + "\n")
    stats_lines = ["--- Übersicht pro Bemaßungsstil ---"]
    total = sum(style_counts.values())
    if target_styles:
        for style in target_styles:
            count = style_counts.get(style, 0)
            stats_lines.append(f"{style}: {count}")
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


def write_xlsx(output_path_xlsx, leaders, final_keys, style_counts, target_styles, na_value="NA"):
    import xlsxwriter
    header = ["text", "dimstyle"] + final_keys
    workbook = xlsxwriter.Workbook(output_path_xlsx)
    ws = workbook.add_worksheet("leaders")
    for c, name in enumerate(header):
        ws.write(0, c, name)
    row_idx = 1
    csv_rows = []
    csv_rows.append(header)
    for item in leaders:
        row_vals = [item["text"], item["dimstyle"]]
        user = item["user"]
        for key in final_keys:
            v = user.get(key, na_value)
            try:
                sv = str(v).strip()
            except Exception:
                sv = v
            row_vals.append(v if sv != "" else na_value)
        for c, val in enumerate(row_vals):
            ws.write(row_idx, c, val)
        csv_rows.append([str(v) if v is not None else "" for v in row_vals])
        row_idx += 1
    ws2 = workbook.add_worksheet("stats")
    ws2.write(0, 0, "style"); ws2.write(0, 1, "count")
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
    # CSV mirror next to XLSX
    try:
        csv_path = os.path.splitext(output_path_xlsx)[0] + ".csv"
        import io, csv as _csv
        with io.open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = _csv.writer(f)
            for row in csv_rows:
                writer.writerow(row)
    except Exception:
        pass


