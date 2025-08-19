## Usage

So verwendest du das RhinoLeaderTool in Rhino.

### 1) Voraussetzungen prüfen
- Die verwendeten DimStyles existieren im aktiven Dokument:
  - „Standard 1:10 Rahmenbeschriftung“
  - „Standard 1:10 Zargenbeschriftung“
  - „Standard 1:10 Schiebetürbeschriftung“
  - „Standard 1:10 Rahmenbeschriftung WHG Eingang“ (falls `rahmentuere_w` genutzt wird)
  - „Standard 1:10 Spez.Rahmenbeschriftung“ (falls `spez` genutzt wird)
- Die CSV-Dateien liegen im Projektordner und enthalten je zwei Spalten: `Schluessel, Wert`.
- Optional: `LeaderAnnotationTemplate.3dm` liegt im Projekt-Root. Fehlt ein DimStyle, wird daraus importiert.

### 2) Aliases in Rhino anlegen
Öffne in Rhino: Options → Aliases → Neuer Alias. Hinterlege z. B.:

```text
bbrt  !_-RunPythonScript "C:\\Users\\<BENUTZER>\\source\\repos\\work\\library\\RhinoLeaderTool\\run_rahmentuere.py"
bbzt  !_-RunPythonScript "C:\\Users\\<BENUTZER>\\source\\repos\\work\\library\\RhinoLeaderTool\\run_zargentuere.py"
bbrtw !_-RunPythonScript "C:\\Users\\<BENUTZER>\\source\\repos\\work\\library\\RhinoLeaderTool\\run_rahmentuere_w.py"
bbst  !_-RunPythonScript "C:\\Users\\<BENUTZER>\\source\\repos\\work\\library\\RhinoLeaderTool\\run_schiebetuere.py"
bbsp  !_-RunPythonScript "C:\\Users\\<BENUTZER>\\source\\repos\\work\\library\\RhinoLeaderTool\\run_spez.py"
```

Passe `<BENUTZER>` an. Alternativ kannst du die Pfade in den `run_*.py` Dateien anpassen, falls dein Repository an einem anderen Ort liegt.

### 3) Ausführen in Rhino
1. Tippe einen Alias in die Befehlszeile, z. B. `bbrt`.
2. Setze die Leader-Punkte (Start, Knick, Textposition). Das Skript verwendet `_Leader` mit Pausen.
3. Nach Abschluss wird der Leader erzeugt, der DimStyle gesetzt und die UserText-Werte aus der CSV angehängt.

### 4) Datenquellen (CSV)
- Jede CSV steht für einen Typ und liegt im Projektordner, z. B. `rahmentuere.csv`.
- Format je Zeile: `Schluessel, Wert`
- Beispiel:

```text
Mauerlichtbreite,1080
Mauerlichthöhe,2140
Mauerstärke,250
```

### 5) Einen neuen Typ hinzufügen
1. Lege eine neue CSV an, z. B. `tuer_xyz.csv`.
2. Ergänze in `config.json` unter `types` einen Eintrag:

```python
"tuer_xyz": {"dimstyle": "Mein DimStyle Name", "csv": "tuer_xyz.csv"},
```

3. Stelle sicher, dass der DimStyle im Dokument existiert.
4. Optional: Lege ein neues Runner-Skript `run_tuer_xyz.py` an (siehe bestehende `run_*.py`).
5. Lege in Rhino einen Alias an, der das Runner-Skript aufruft.

### 7) Logging konfigurieren
- In `config.json` unter `logging` kann der Modus gewählt werden:
  - `"mode": "csv"` (Standard) → `created_leaders_log.csv`
  - `"mode": "xlsx"` → `created_leaders_log.xlsx` (benötigt `openpyxl` in Rhino-Python)

### 6) Alternative: Alias-dynamische Variante
- Das Skript `leader_usertext_dynamic.py` kann den verwendeten Alias aus der Command History lesen und daraus CSV und DimStyle bestimmen. Dafür das interne `mapping` anpassen.

### Fehlerbehebung
- Meldung „Bemaßungsstil nicht gefunden“: DimStyle-Name im Dokument prüfen.
- „Kein Leader erstellt“: Setz die drei Leader-Punkte ab und bestätige den Befehl.
- „Alias nicht erkannt“ (dynamisch): Alias-Schreibweise und Mapping prüfen.


