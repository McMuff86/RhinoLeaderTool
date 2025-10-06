## Future Improvements

### Robustness & UX
- Validierung der CSV-Inhalte (leere Werte, nicht erlaubte Schlüssel) mit klaren Meldungen.
- Optionale Vorschau: Vor dem Schreiben der UserText-Werte eine Zusammenfassung anzeigen und bestätigen lassen.
- Bessere Fehlerbehandlung und Logging (z. B. Log-Datei im Projektordner).

### Konfiguration & Erweiterbarkeit
- Zentrales Konfigurationsfile (z. B. `config.json`) für die Typ→(DimStyle, CSV)-Zuordnung statt hartem Mapping im Code.
- Unterstützung relativer/konfigurierbarer Pfade, um verschiedene Repository-Standorte zu erlauben.
- Mapping der Aliases und Typen aus Datei laden; Hot-Reload ohne Rhino-Neustart.

### Funktionen rund um DimStyles
- Falls DimStyle fehlt: Option anbieten, automatisch aus Template zu importieren.
- Pro-Typ individuelle Leader-Text-Templates (z. B. generierter Text aus CSV-Werten).

### Datenmodell & Qualität
- Schema-Definition für CSV-Keys (Pflichtfelder, Datentypen, gültige Wertebereiche).
- Tooling-Skript zum Prüfen aller CSV-Dateien gegen das Schema.

### Bedienung & Integration
- Toolbar-Buttons in Rhino für die wichtigsten Typen (Icons + Tooltipps).
- Menüeinträge unter „Tools“ oder „Scripts“.
- Optionaler UI-Dialog (Eto.Forms) zum Auswählen des Typs, DimStyles und CSV vor dem Erstellen.

### Technische Verbesserungen
- Statt `exec`-Laden: Modulimport mit klaren Funktionsaufrufen, um Scope zu kapseln.
- Unit-Tests für Mapping, CSV-Parser und Hilfsfunktionen (soweit Rhino-APIs mockbar).
- Typkonvertierungen (Zahl, Text, Bool) automatisch aus CSV ableiten.

### Dokumentation
- Screenshots/GIFs des Workflows in README/USAGE.
- Schritt-für-Schritt Guide für das Anlegen neuer DimStyles im Büro-Template.

### Berechnung der Bandhöhen ([Bandmass_1_c,227],[Bandmass_2_b,1620],[Bandmass_3_d,250])
- Einfügewertre via csv in Bezug auf "Lichthöhe" -> Lichthöhe,2100 : Anordnung_Band_Schloss_Elkuch.csv


