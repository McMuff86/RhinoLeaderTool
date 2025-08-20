#! python 3
import os, sys
user_dir = os.path.expanduser("~")
base = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")
if base not in sys.path:
    sys.path.append(base)

from migrate_leader_usertext_keys import bulk_update_key_for_leaders

# Alle Leader, Wert immer setzen (auch wenn bereits vorhanden) -> option A
# bulk_update_key_for_leaders("Haus", "A", only_if_missing=False, styles=None, write_report=True)

'''
# Mit Stilfilter -> option B
bulk_update_key_for_leaders("Betriebsauftrag", "25.0591-201", styles=[
    "Standard 1:10 Rahmenbeschriftung",
    "Standard 1:10 Zargenbeschriftung",
    "Standard 1:10 Schiebetürbeschriftung",
    "Standard 1:10 Rahmenbeschriftung WHG Eingang",
    "Standard 1:10 Spez.Rahmenbeschriftung"
], write_report=True)
'''
'''
# Mit Stilfilter -> option B
bulk_update_key_for_leaders("Haus", "B", styles=[
    "Standard 1:10 Rahmenbeschriftung",
    "Standard 1:10 Zargenbeschriftung",
    "Standard 1:10 Schiebetürbeschriftung",
    "Standard 1:10 Rahmenbeschriftung WHG Eingang",
    "Standard 1:10 Spez.Rahmenbeschriftung"
], write_report=True)
'''

'''
# Mit Stilfilter -> option B
bulk_update_key_for_leaders("Betriebsauftrag", "25.0591-201_002", styles=[
    "Standard 1:10 Rahmenbeschriftung",
    "Standard 1:10 Rahmenbeschriftung WHG Eingang",
], write_report=True)
'''

'''
# Mit Stilfilter -> option B
bulk_update_key_for_leaders("Betriebsauftrag", "25.0591-201_001", styles=[
    "Standard 1:10 Zargenbeschriftung",
], write_report=True)
'''

'''# Mit Stilfilter -> option B
bulk_update_key_for_leaders("Farbe_Futterseite", "NCS S 5010-Y30R matt (Ockerbraun)", styles=[
"Standard 1:10 Zargenbeschriftung",
], write_report=False)
'''
'''
# Mit Stilfilter -> option B
bulk_update_key_for_leaders("Türblattdicke", "39", styles=[
"Standard 1:10 Zargenbeschriftung",
], write_report=False)
'''
'''
# Mit Stilfilter -> option B
bulk_update_key_for_leaders("Farbe_Futterseite", "46", styles=[
"Standard 1:10 Rahmenbeschriftung WHG Eingang",
], write_report=False)
'''

# option C
# bulk_update_key_for_leaders("Haus", "A", only_if_missing=True, styles=None, write_report=True)

'''
# Beispiel D: Nur leere/NA-Werte setzen (kombiniert)
from migrate_leader_usertext_keys import load_config
cfg = load_config()
na = cfg.get("export", {}).get("na_value", "NA")

def update_only_na(key, new_val):
    # only_if_missing=True deckt nur leere Strings ab; hier filtern wir zusätzlich NA
    bulk_update_key_for_leaders(key, new_val, only_if_missing=True, styles=None, write_report=True)

# Beispielaufruf:
# update_only_na("Betriebsauftrag", "25.0000-001")
'''


#Beispiel E: Alle DimStyles (target_styles leer in config.json) und ohne Report
bulk_update_key_for_leaders("Lichthöhe", "NA", styles=None, write_report=False)


'''
# Beispiel F: Mehrere Keys nacheinander setzen
# bulk_update_key_for_leaders("Haus", "A", styles=None, write_report=False)
# bulk_update_key_for_leaders("Betriebsauftrag", "25.0591-201", styles=None, write_report=True)
'''