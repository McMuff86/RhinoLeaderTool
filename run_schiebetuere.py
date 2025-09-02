#! python 3
# -*- coding: utf-8 -*-
import os

typ = "schiebetuere"

import sys
try:
    _self = sys.argv[0] if (hasattr(sys, 'argv') and sys.argv) else None
except Exception:
    _self = None
if _self and os.path.isfile(_self):
    base_dir = os.path.dirname(os.path.abspath(_self))
elif '__file__' in globals():
    base_dir = os.path.dirname(os.path.abspath(__file__))
else:
    base_dir = os.getcwd()
script_path = os.path.join(base_dir, "main_leader_script.py")

try:
    with open(script_path, "r", encoding="utf-8") as f:
        code = f.read()
except Exception as e:
    print("Could not load main_leader_script.py:", e)
else:
    try:
        exec(code + f"\nrun_leader_for_type('{typ}')")
    except Exception as e:
        print("Error executing leader script:", e)
