## RhinoLeaderTool – Agent Overview

This document gives agents a current, high-signal map of the RhinoLeaderTool workspace: what exists, what it does, how to run it, and where deeper docs live.

### Repository structure (top-level)
- `config.json`: Central configuration (types, presets, defaults, logging, template import, aliases)
- `export_presets.json`: Shared presets for export dialog (keys and leader types)
- `LeaderAnnotationTemplate.3dm`: Source for missing dimension styles
- `run_*.py`: Entry points for specific leader types
- `main_leader_script.py`: Core leader creation logic
- `leader_usertext_dynamic.py`: Dynamic variant that infers type via alias/command history
- `leader_usertext_from_csv.py`: Legacy helper to attach user text from a CSV
- `migrate_leader_usertext_keys.py`: Migrates existing leaders to the current user text schema
- `sync_leader_usertext.py`: Eto dialog to edit/apply defaults to leaders
- `write_leaders_to_file.py`: Export to TXT/CSV/XLSX with dialogs, filtering and presets (now includes robust per-cell commit)
- `calc_engine.py`: Calculation rules (Elkuch band masses wrapper)
- `rhino_sync.py`: RhinoCommon helpers (thread-safe UserText write)
- `import_leaders_from_excel.py`: Import helpers for leaders from Excel (if used in your flow)
- `sort_and_update_csvs.py`: Keeps CSV keys alphabetized, fills missing keys
- `bulk_update_KeyValue.py`: Batch update a single key across leaders
- `csv_template/`: CSV templates per leader type (project-specific variants allowed)
- `docs/`: All markdown docs (README, USAGE, FUTURE_IMPROVEMENTS, CHANGELOG, AGENTS)

### How to run
- Set Rhino aliases from `export_alias_RhinoV2.txt`
- Run leader creation via alias; or run `write_leaders_to_file.py` to preview/export
- Ensure `config.json` points to `LeaderAnnotationTemplate.3dm` and CSVs


