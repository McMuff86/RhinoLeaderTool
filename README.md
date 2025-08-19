## RhinoLeaderTool

Ein kleines Rhino-Python Werkzeug, um Leader-Beschriftungen mit vordefinierten Bemaßungsstilen zu erstellen und automatisch UserText (Schlüssel/Wert-Paare) aus CSV-Dateien an den erzeugten Leader zu hängen.

### Kernidee
- Beim Aufruf eines Alias (z. B. `bbrt`) wird ein Runner-Skript gestartet.
- Dieses lädt `main_leader_script.py` und ruft `run_leader_for_type(<typ>)` auf.
- Das Skript lässt dich einen Leader interaktiv platzieren und setzt danach:
  - den gewünschten Bemaßungsstil (DimStyle) am Leader,
  - die UserText-Attribute aus einer passenden CSV-Datei.

### Features
- **Automatisierte UserText-Zuweisung**: CSV-Schlüssel/Werte werden an den Leader geschrieben.
- **DimStyle-Auswahl pro Typ**: Jeder Tür-Typ nutzt einen definierten Bemaßungsstil.
- **Einfache Erweiterbarkeit**: Neue Typen durch eine CSV, einen Mapping-Eintrag und optional einen Alias hinzufügen.

### Unterstützte Typen (Stand jetzt)
- `rahmentuere` → `rahmentuere.csv` → DimStyle: „Standard 1:10 Rahmenbeschriftung“
- `zargentuere` → `zargentuere.csv` → DimStyle: „Standard 1:10 Zargenbeschriftung“
- `schiebetuere` → `schiebetuere.csv` → DimStyle: „Standard 1:10 Schiebetürbeschriftung“
- `rahmentuere_w` → `rahmentuerew.csv` → DimStyle: „Standard 1:10 Rahmenbeschriftung WHG Eingang“
- `spez` → `spez.csv` → DimStyle: „Standard 1:10 Spez.Rahmenbeschriftung“

### Ordnerstruktur (relevant)
- `main_leader_script.py`: Kernlogik (Leader erzeugen, DimStyle setzen, UserText aus CSV anhängen)
- `run_*.py`: Runner-Skripte, die den passenden Typ setzen und `main_leader_script.py` ausführen
- `*.csv`: Schlüssel/Wert-Listen für UserText, die an den Leader gehängt werden
- `export_alias_Rhino*.txt`: Beispiel-Aliases zum Starten der Runner aus Rhino
- `leader_usertext_dynamic.py`: Alternative Variante, die den benutzten Alias aus der Command History ermittelt

### Voraussetzungen
- Rhino mit Python-Scripting (rhinoscriptsyntax)
- Die verwendeten Bemaßungsstile müssen im aktiven Rhino-Dokument existieren (Name muss passen)
- Das Repository liegt (standardmäßig) unter `C:\Users\<BENUTZER>\source\repos\work\library\RhinoLeaderTool`

### Installation (kurz)
1. Repository an den gewünschten Pfad klonen/kopieren.
2. In Rhino unter „Options → Aliases“ die gewünschten Alias-Zeilen eintragen (siehe `export_alias_RhinoV2.txt`) und Pfade bei Bedarf anpassen.
3. Sicherstellen, dass die im Mapping referenzierten DimStyles im Dokument vorhanden sind.

### Funktionsweise (intern)
- `run_<typ>.py` setzt eine Variable `typ` und lädt den Code aus `main_leader_script.py` per `exec(...)`.
- `main_leader_script.py` enthält:
  - CSV-Einlesen (`read_csv_attributes`)
  - DimStyle-Suche (`get_dimstyle_id`)
  - Leader-Erstellung über Rhino-Befehl `_Leader` (mit Pausen für deine Punkteingaben)
  - Ersetzen des DimStyle am neu erzeugten Leader
  - Zuweisen der UserText-Attribute aus der CSV
- Der CSV-Pfad wird dynamisch aus deinem Benutzerverzeichnis aufgebaut, damit keine hardcodierten Benutzer-Namen nötig sind.

### Beispiel-Aliases
Aus `export_alias_RhinoV2.txt` (Pfade ggf. anpassen):

```bash
bbrt !_-RunPythonScript "C:\Users\adrian.muff\source\\repos\work\library\RhinoLeaderTool\run_rahmentuere.py"
bbzt !_-RunPythonScript "C:\Users\adrian.muff\source\\repos\work\library\RhinoLeaderTool\run_zargentuere.py"
bbrtw !_-RunPythonScript "C:\Users\adrian.muff\source\\repos\work\library\RhinoLeaderTool\run_rahmentuere_w.py"
bbst !_-RunPythonScript "C:\Users\adrian.muff\source\\repos\work\library\RhinoLeaderTool\run_schiebetuere.py"
bbsp !_-RunPythonScript "C:\Users\adrian.muff\source\\repos\work\library\RhinoLeaderTool\run_spez.py"
```

### Lizenz
Interne Nutzung. Falls du eine formale Lizenz benötigst, ergänze sie hier.


