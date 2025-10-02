# RhinoLeaderTool Agent Guide

This document describes how to operate and extend the RhinoLeaderTool with a focus on automation, prompts, and per-document configuration. It complements `README.md` and `USEAGE.md` and links to relevant scripts.

## Purpose

- Create annotated leaders in Rhino with predefined Dimension Styles and attach UserText key/value pairs from CSV templates.
- Allow per-document selection of a CSV folder so that the same template name (e.g. `rahmentuerew.csv`) can exist with different values per project/order.

## Key Files

- `main_leader_script.py`: core flow to place leaders, set DimStyle, merge globals and type-specific values, attach UserText, and log.
- `run_*.py`: thin launchers for each type; they call `run_leader_for_type(<typ>)` from `main_leader_script.py`.
- `leader_usertext_dynamic.py`: dynamic variant that infers the type from the command alias and follows the same CSV resolution rules.
- `write_leaders_to_file.py` and `write_leaders_to_file_bupc.py`: export of leaders and their UserText to text/Excel. Now resolve required keys against the selected CSV folder.
- `migrate_leader_usertext_keys.py`: migration and bulk-update utilities. Also resolves required keys against the selected CSV folder.
- `config.json`: central configuration (types, defaults, logging, aliases, template path, export NA value).
- See also: `README.md` (overview) and `USEAGE.md` (usage details and alias set-up).

## Per-Document CSV Folder

Goal: Projects can maintain their own CSV templates for the same types without changing repository defaults.

### Storage

- Stored in Rhino DocumentData: section `RhinoLeaderToolGlobals`, key `CsvFolder`.

### Selection Flow

1. On first use, the tool prompts to select a CSV folder using a folder picker.
2. The chosen path is saved to DocData. Subsequent operations re-use it.
3. If not set, the tool falls back to `config.json.base_path` and finally to the default repository path `C:\Users\<USER>\source\repos\work\library\RhinoLeaderTool`.

### Where Implemented

- `main_leader_script.py`: function `get_selected_csv_folder(...)` and integration in `run_leader_for_type(typ)`.
- `leader_usertext_dynamic.py`: same logic for the dynamic launcher.
- `write_leaders_to_file.py`, `write_leaders_to_file_bupc.py`: use the selected folder when computing required keys and performing exports.
- `migrate_leader_usertext_keys.py`: use the selected folder to compute the union of required keys from CSVs.

### Impact

- Allows multiple, order-specific CSVs with identical filenames but different values.
- Keeps global config minimal and avoids manual path edits in code.

## Types and Presets

- Types and default CSVs are defined in `config.json` under `types`.
- Some types support named presets which map to different CSV files (e.g., `Standard`, `Nebenraum Typ1`). The preset name is written to UserText (`Preset`).

## Global and Type-Specific Values

- Global prompts (e.g., `Haus`, `Betriebsauftragsposition`) are configured in `config.json.defaults` and saved per document to DocData.
- Type-specific prompts (e.g., `Betriebsauftrag`) are also supported and saved under the `RhinoLeaderToolType:<typ>` DocData section.
- Values are merged into the CSV data; missing or NA values can be overridden by `defaults.usertext_overrides`.

## Export and Logging

- Exports: TXT/CSV or XLSX (see `write_leaders_to_file.py`, `write_leaders_to_file_bupc.py`).
- Logging: CSV/XLSX via `logging.mode` and `logging.file` in `config.json`, with fallback to CSV if Excel libraries are not available.

## Quick Links

- Overview: see `README.md`.
- How to use (aliases, steps, CSV format): see `USEAGE.md`.
- Scripts: `main_leader_script.py`, `run_*.py`, `leader_usertext_dynamic.py`, `migrate_leader_usertext_keys.py`, `write_leaders_to_file.py`.
- Preview UI (List & Table) implementation notes: `docs/preview_export_ui.md` (incl. Rhino Eto docs link)

## Operational Tips

- If a needed DimStyle is missing, the tool imports from `LeaderAnnotationTemplate.3dm` (path configurable).
- To switch CSV sets for a document, clear or update `CsvFolder` via `Rhino → Document Data` or re-run a script that prompts for the folder and select a new path.
- Keep CSVs in a dedicated project subfolder (e.g., `.../ProjectX/csv/`) for clarity.


