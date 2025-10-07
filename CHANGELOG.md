## Changelog

All notable changes to this project will be documented in this file.

### [Unreleased]
- Modularization groundwork: added `rhino_sync.py`, `calc_engine.py`
- Export preview per-cell commit via RhinoCommon with UI-thread invocation
- Docs moved under `docs/` (README, USEAGE, FUTURE_IMPROVEMENTS, AGENTS)

### 2025-10-02
- Export dialog: add type filter, path+filename selection
- Export dialog: two-column, scrollable key selector; select all/none
- Export presets: switched from DocData to workspace `export_presets.json`
- Presets now include type selection (types_all/types) and keys (all_keys/keys)
- Fix stats generation and leader detection in export
- Add new CSV key: `Zargen Bemerkung` to all templates
- Numerous Eto constructor fixes and robust dialog fallbacks


