#! python 3
# -*- coding: utf-8 -*-
import os

typ = "schiebetuere"

user_dir = os.path.expanduser("~")
script_path = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool", "main_leader_script.py")

with open(script_path, "r", encoding="utf-8") as f:
    code = f.read()

# Übergibt den Wert von 'typ' an das Skript-Kontext
exec(code + f"\nrun_leader_for_type('{typ}')")
