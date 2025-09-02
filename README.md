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

### Best Practice: CSV-Ordner pro Projekt (rekursiv)
- Beim ersten Start fragt das Tool nach einem CSV-Ordner. Dieser wird im Dokument gespeichert (`RhinoLeaderToolGlobals/CsvFolder`).
- Ab diesem Ordner sucht das Tool benötigte CSV-Dateien rekursiv (Unterordner werden berücksichtigt).
- Vorteil: Identische Dateinamen (z. B. `rahmentuerew.csv`) können pro Auftrag unterschiedliche Werte haben.
- Konfliktfall (mehrere Treffer): Das Tool wählt die „nächstliegende“ Datei (kürzester relativer Pfad). Optional wird eine Auswahl angezeigt; die Entscheidung wird im Dokument gespeichert (`RhinoLeaderToolCsvMap`).

### Installation (kurz)
1. Repository an den gewünschten Pfad klonen/kopieren.
2. In Rhino unter „Options → Aliases“ die gewünschten Alias-Zeilen eintragen (siehe `export_alias_RhinoV2.txt`) und Pfade bei Bedarf anpassen.
3. Sicherstellen, dass die im Mapping referenzierten DimStyles im Dokument vorhanden sind.

### Konfiguration (config.json)
- Im Projekt-Root kann eine `config.json` abgelegt werden. Fehlt sie, wird eine Default-Konfiguration verwendet.
- Wichtige Schlüssel:

```json
{
  "base_path": "C:/Users/<BENUTZER>/source/repos/work/library/RhinoLeaderTool",
  "template_path": "LeaderAnnotationTemplate.3dm",
  "logging": { "mode": "csv", "file": "created_leaders_log.csv" },
  "types": {
    "rahmentuere": {"dimstyle": "Standard 1:10 Rahmenbeschriftung", "csv": "rahmentuere.csv"}
  }
}
```

### CSV-Schlüssel (aktuell)
- Planwerte: `Mauerlichtbreite_plan`, `Mauerlichthöhe_plan`, `Mauerstärke_plan`
- Massaufnahme: `Mauerlichtbreite_Massaufnahme`, `Mauerlichthöhe_Massaufnahme_ab_MtR`, `Mauerlichthöhe_Massaufnahme`, `Mauerstärke_Massaufnahme`

Beispiel:
```text
Mauerlichtbreite_plan,1080
Mauerlichthöhe_plan,2140
Mauerstärke_plan,250
Mauerlichtbreite_Massaufnahme,
Mauerlichthöhe_Massaufnahme_ab_MtR,
Mauerlichthöhe_Massaufnahme,
Mauerstärke_Massaufnahme,
```

### Automatischer DimStyle-Import
- Falls ein benötigter DimStyle fehlt, importiert das Skript DimStyles aus `LeaderAnnotationTemplate.3dm` (Pfad per `config.json` steuerbar) und versucht es erneut.

### Logging
- Standard: CSV-Log `created_leaders_log.csv` im `base_path`.
- Optional: Excel-Log (`logging.mode = "xlsx"`). Erfordert `openpyxl`. Bei Fehlern fällt das Skript automatisch auf CSV zurück.

### Funktionsweise (intern)
- `run_<typ>.py` setzt eine Variable `typ` und lädt den Code aus `main_leader_script.py` per `exec(...)`.
- `main_leader_script.py` enthält:
  - CSV-Einlesen (`read_csv_attributes`)
  - DimStyle-Suche (`get_dimstyle_id`)
  - Leader-Erstellung über Rhino-Befehl `_Leader` (mit Pausen für deine Punkteingaben)
  - Ersetzen des DimStyle am neu erzeugten Leader
  - Zuweisen der UserText-Attribute aus der CSV
- CSV-Auflösung: Zuerst per-Dokument CSV-Ordner (DocData), dann rekursive Suche darin. Keine hardcodierten Benutzer-Namen nötig.

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


