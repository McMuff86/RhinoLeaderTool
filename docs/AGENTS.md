# RhinoLeaderTool – Agent Guide

This document provides AI agents with a comprehensive, up-to-date map of the RhinoLeaderTool workspace: what exists, what it does, how to run it, critical implementation details, and where to find deeper documentation.

**🔍 IMPORTANT: Before starting any task, always:**
1. **Explore the workspace structure** using `list_dir` and `glob_file_search`
2. **Read relevant files** to understand current implementation
3. **Search the codebase** semantically for similar patterns before implementing new features
4. **Check this document** for known patterns and solutions

---

## 📁 Repository Structure

### Core Scripts
- **`config.json`**: Central configuration hub
  - Leader types with DimStyles and CSV mappings
  - Export settings (NA values, sorting rules, floor sorting)
  - Presets per type
  - Rhino alias mappings
  - Template 3dm path for auto-import of missing dimension styles

- **`export_presets.json`**: Shared presets for export dialog
  - Saved key selections
  - Leader type filters
  - Managed via UI, persisted to file

- **`config_io.py`**: Configuration loading and path resolution helpers

### Leader Creation
- **`main_leader_script.py`**: Core leader creation logic
  - DimStyle selection
  - CSV-based UserText population
  - Document defaults integration
  
- **`leader_usertext_dynamic.py`**: Dynamic type inference via alias/command history

- **`run_*.py`**: Type-specific entry points (`run_rahmentuere.py`, `run_zargentuere.py`, etc.)

### Export & Preview System
- **`write_leaders_to_file.py`**: Main export orchestrator
  - Leader data collection from Rhino document
  - Eto dialog for export options
  - Format output (TXT, CSV, XLSX via `export_writer.py`)
  - **CRITICAL**: Reloads leaders after preview/commit to capture UserText changes
  
- **`export_ui.py`**: Eto-based preview dialog with editable table
  - TreeGridView for data display/editing
  - Search/filter functionality
  - Commit changes to Rhino UserText
  - **See "Eto Dialog Patterns" section for implementation details**

- **`export_writer.py`**: File writing logic (TXT, XLSX with xlsxwriter)

### Data Sync & Migration
- **`sync_leader_usertext.py`**: Eto dialog to edit/sync document defaults to leaders

- **`migrate_leader_usertext_keys.py`**: Schema migration tool
  - Adds new keys across all leaders
  - Sets `LeaderGUID`, `SchemaVersion`
  - Fills missing values with NA

- **`rhino_sync.py`**: Thread-safe RhinoCommon helpers
  - `write_usertext_ui()`: UI-thread-safe UserText write with undo support

### Calculations
- **`calc_engine.py`**: Business logic for Elkuch band mass calculations
  - Maps `Lichthöhe` → Band positions (B, C, D, M)
  - Integrates with `Anordnung_Band_Schloss_Elkuch.CSV`

### Utilities
- **`sort_and_update_csvs.py`**: Maintains alphabetized CSV keys
- **`bulk_update_KeyValue.py`**: Batch update single key across leaders
- **`import_leaders_from_excel.py`**: Excel import helpers (if needed)

### Templates & Data
- **`csv_template/rogg/*.csv`**: Leader type templates
  - `rahmentuere.csv`, `zargentuere.csv`, `schiebetuere.csv`, etc.
  - Alphabetically sorted keys
  - Project-specific variants (`zargentuere_Keller_EI30.csv`)

- **`LeaderAnnotationTemplate.3dm`**: Source file for DimStyle import
- **`Anordnung_Band_Schloss_Elkuch.CSV`**: Band mass calculation lookup table

### Documentation
- **`docs/`**: All markdown documentation
  - `README.md`: Documentation index
  - `USAGE.md`: Daily usage guide
  - `FUTURE_IMPROVEMENTS.md`: Roadmap and ideas
  - `AGENTS.md`: This file
  - `preview_export_ui.md`: Export UI documentation

- **Root `README.md`**: Main project overview (stays in root for GitHub visibility)
- **Root `CHANGELOG.md`**: Version history (stays in root per convention)

---

## 🔧 Key Features & Implementation

### Leader Creation Flow
1. User runs type-specific script (`run_rahmentuere.py`)
2. Script loads CSV template for that type
3. Displays dialog for DimStyle selection
4. Creates leader at cursor with UserText from CSV
5. Stores document defaults for future leaders

### Export & Preview System
1. **Data Collection** (`write_leaders_to_file.py`):
   - Scans `sc.doc.Objects` for `Rhino.Geometry.Leader` instances
   - Filters by DimStyle if types selected
   - Extracts text + all UserText keys

2. **Preview Dialog** (`export_ui.py`):
   - Shows leaders in editable TreeGridView
   - User can edit values directly in cells
   - Search/filter functionality
   - Commit changes back to Rhino

3. **Post-Commit Reload** ⚠️ **CRITICAL PATTERN**:
   ```python
   # After preview dialog closes, reload leaders to get committed changes
   leaders, all_user_keys, style_counts, export_lines_text = _load_leaders_from_document(
       target_styles, required_keys, export_all_keys, selected_keys, cfg
   )
   ```

4. **Export**: Writes to TXT/CSV/XLSX with calculated values, stats sheet

### Calculation System
- **Auto-fill Band Masses** (`write_leaders_to_file.py`):
  - Reads `Lichthöhe` + `Bandanzahl` from UserText
  - Looks up Elkuch CSV for correct positions
  - Fills `Bandmass_1_c`, `Bandmass_2_b`, `Bandmass_3_d` (or `_m`)
  - Respects "calc" placeholder vs. actual values
  - Configurable via `config.json`: `export.override_bandmasse`

---

## 🎨 Eto Dialog Patterns (IronPython/Rhino)

### CRITICAL: Event Handler Garbage Collection Prevention

**Problem**: In IronPython, event handlers attached to Eto controls are garbage-collected if not stored in a persistent reference.

**Solution**:
```python
def show_dialog():
    # CRITICAL: Create handler_refs at function scope, NOT in a nested try-block
    handler_refs = []
    
    dialog = forms.Dialog()
    btn = forms.Button()
    
    def on_click(sender, e):
        dialog.Close()
    
    # Store handler BEFORE attaching
    handler_refs.append(on_click)
    btn.Click += on_click
    
    # Attach to dialog to keep alive
    dialog._handler_refs = handler_refs
    
    dialog.ShowModal()
```

**Key Points**:
- ✅ Define `handler_refs = []` at the **function scope** (not inside try-blocks)
- ✅ `append()` handlers **BEFORE** attaching them to controls
- ✅ Attach `handler_refs` to dialog: `dialog._handler_refs = handler_refs`
- ❌ Never rely on handlers without storing them

### Dialog Close Pattern

**Problem**: `dialog.Close()` in Rhino **does not accept arguments**.

**Solution**:
```python
dialog.Tag = False  # Initialize return value

def on_ok(sender, e):
    dialog.Tag = True   # Set BEFORE closing
    dialog.Close()      # No argument!

def on_cancel(sender, e):
    dialog.Tag = False
    dialog.Close()

# After ShowModal, read Tag
dialog.ShowModal()
return bool(dialog.Tag)
```

### .NET Collection Iteration

**Problem**: .NET collections like `ITreeGridStore` are **not directly iterable** with Python's `for item in collection`.

**Solution**:
```python
# ❌ WRONG - not iterable
for item in grid.DataStore:
    process(item)

# ✅ CORRECT - use Count and indexer
total = grid.DataStore.Count
for i in range(total):
    item = grid.DataStore[i]
    process(item)
```

### Thread-Safe UserText Writes

Always use `rhino_sync.write_usertext_ui()` for UI-triggered writes:
```python
from rhino_sync import write_usertext_ui

# Automatically runs on UI thread, wraps in undo record
success = write_usertext_ui(obj_id, "KeyName", "value")
```

---

## 🚀 How to Run

### Setup
1. Set Rhino aliases from `export_alias_RhinoV2.txt`
2. Ensure `config.json` points to correct paths:
   - `template_path`: Path to `LeaderAnnotationTemplate.3dm`
   - `types[].csv`: Paths to CSV templates

### Create Leaders
```
# In Rhino command line
rahmentuere     # Creates Rahmentüre leader
zargentuere     # Creates Zargentüre leader
```

### Export Leaders
```
# In Rhino, run Python script
write_leaders_to_file.py
```
- Opens dialog to select types, keys, destination
- Shows preview with editable table
- Commit changes, then export to XLSX/TXT

---

## 🐛 Common Debugging Patterns

### Eto Dialog Not Responding
1. **Check handler_refs scope**: Must be at function level
2. **Verify handlers stored**: `handler_refs.append(handler)` before `control.Event += handler`
3. **Add debug prints**: 
   ```python
   print("[Debug] Button clicked")
   print("[Debug] Handler result:", result)
   ```

### Export Shows Old Values After Commit
- **Cause**: Leaders not reloaded after commit
- **Fix**: Call `_load_leaders_from_document()` after preview closes

### DataStore Iteration Fails
- **Error**: `'ITreeGridStore' object is not iterable`
- **Fix**: Use `range(ds.Count)` and `ds[i]` indexing

---

## 📚 Agent Task Checklist

When working on this project:

- [ ] **Explore workspace structure** before coding
- [ ] **Read relevant existing files** to understand patterns
- [ ] **Search codebase semantically** for similar implementations
- [ ] **Follow Eto patterns** documented above for UI work
- [ ] **Test in Rhino** after changes (modules are cached!)
- [ ] **Update this document** if adding new patterns or fixes
- [ ] **Check `config.json`** for configurable options before hardcoding
- [ ] **Use `rhino_sync.write_usertext_ui()`** for UserText writes
- [ ] **Store event handlers** in `handler_refs` for Eto dialogs

---

## 🔮 Future Improvements

See `docs/FUTURE_IMPROVEMENTS.md` for full roadmap. Key items:
- Cloud/shared storage for presets
- Unit tests for CSV parsing
- Localization for Eto dialogs
- CLI wrappers for headless export
- Enhanced preset import/export UI

---

## 📞 Quick Reference

| Task | File | Key Function/Pattern |
|------|------|---------------------|
| Create leader | `main_leader_script.py` | `create_leader_with_usertext()` |
| Export to file | `write_leaders_to_file.py` | `export_leader_texts()` |
| Show preview | `export_ui.py` | `show_preview_dialog()` |
| Write UserText | `rhino_sync.py` | `write_usertext_ui(obj_id, key, val)` |
| Eto dialog | Any `*_ui.py` | See "Eto Dialog Patterns" above |
| Config | `config.json` | Central settings |
| Band calc | `calc_engine.py` + `write_leaders_to_file.py` | `autofill_band_masses_for_export()` |

---

**Last Updated**: 2025-01-07  
**Maintained By**: AI Agents + User Feedback

