# Preview UI for Export (Eto Forms)

This document explains how the preview dialog for write_leaders_to_file.py is implemented: a two-tab UI with a compact List view and a sortable Table view, built with Eto for Rhino 8 / Python 3.

## Goals
- Show all leaders before exporting (text + UserText keys)
- Allow quick filtering via a search box
- Provide two preview modes:
  - List: robust, single-line preview per leader
  - Table: columns for `text`, `dimstyle`, and selected keys; sortable and scrollable
- Keep Export/Cancel buttons always visible, with the content scrollable


## Key Eto concepts used
- Dialog container: `forms.Dialog()` with `Resizable=True` and fixed initial `ClientSize`
- DynamicLayout for overall composition; content placed in a scrollable area to keep buttons visible
- Tabs via `forms.TabControl()` with two `forms.TabPage()` instances
- List view: `forms.ListBox()` bound to a python list of strings; filter via TextChanged on a shared `forms.TextBox()`
- Table view: `forms.TreeGridView()` with explicit `TreeGridItemCollection` as DataStore and `TreeGridItem(values)` per row (stable in Rhino 8 + Python 3)
- Sorting: header-click toggles ascending/descending; we sort the backing list and rebuild the `TreeGridItemCollection`


## Why TreeGridView + TreeGridItem?
Rhino 8 Python 3 interop requires explicit items for tree/grid controls. A list of lists is not implicitly cast. Using `TreeGridItemCollection` and `TreeGridItem([...])` avoids crashes and renders reliably.

Reference: RH-82477 (implicit cast issue) and forum guidance. Also see the official Eto guide for Rhino Python:
- Rhino Developer Docs – Writing Custom Eto forms in Python: [Rhino guide](https://developer.rhino3d.com/guides/rhinopython/eto-forms-python/)


## Structure (simplified)
1) Build `required_keys` and collect leaders (existing export flow)
2) Build preview dialog:
- Search row: `Label("Suche:")` + `TextBox`
   - Tabs
     - List tab: `ListBox` bound to joined text lines
     - Table tab: create columns for `text`, `dimstyle`, then selected keys
       - Build `TreeGridItemCollection`
       - For each leader, create `TreeGridItem([text, dimstyle, key1, key2, ...])`
       - Assign to `TreeGridView.DataStore`
       - Wire sorting: on header click, sort the source list and rebuild the collection
   - Place the content (search + tabs) in a `Scrollable` so buttons remain visible
   - Buttons: Export / Cancel


## Important implementation notes
- Keep the content in a `Scrollable`; place buttons in a separate layout row.
- When sorting/filtering, operate on a "view list" (copy of rows), then rebuild the `TreeGridItemCollection` each time.
- Convert all cell values to strings for display to avoid type issues.
- Limit number of dynamic key columns (e.g., 40) to keep the UI responsive.


## Minimal code pattern for the Table
```python
grid = forms.TreeGridView()
grid.ShowHeader = True

# Columns
col_keys = ["text", "dimstyle", ...]  # append selected keys
def add_col(idx, name):
    c = forms.GridColumn()
    c.HeaderText = name
    c.DataCell = forms.TextBoxCell(idx)
    try: c.Sortable = True
    except: pass
    grid.Columns.Add(c)

# DataStore builder
def build_store(rows):
    items = forms.TreeGridItemCollection()
    for r in rows:
        vals = [str(r.get(k, "")) for k in col_keys]
        items.Add(forms.TreeGridItem(vals))
    return items

# Sort handler (toggle asc/desc)
sort_state = {"key": None, "desc": False}
def on_header_click(sender, e):
    idx = next((i for i, col in enumerate(grid.Columns) if col == e.Column), -1)
    if idx < 0: return
    key = col_keys[idx]
    if sort_state["key"] == key: sort_state["desc"] = not sort_state["desc"]
    else: sort_state["key"], sort_state["desc"] = key, False
    rows = list(view_rows)
    rows.sort(key=lambda r: (r.get(key) is None, str(r.get(key, "")).lower()))
    if sort_state["desc"]: rows.reverse()
    view_rows[:] = rows
    grid.DataStore = build_store(view_rows)

# Wire header clicks (TreeGridView build-dependent)
try:
    grid.ColumnHeaderClick += on_header_click
except:
    for c in grid.Columns:
        try: c.HeaderClick += on_header_click
        except: pass
```
```

## Reuse checklist
- Use `TreeGridView` + `TreeGridItemCollection` for Python 3
- Always convert cell values to strings
- Keep a `view_rows` list and rebuild the DataStore on sort/filter
- Place content in a `Scrollable`; keep buttons separate
- Add a robust search TextBox and hook `TextChanged`


