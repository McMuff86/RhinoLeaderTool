import os
import json


def load_config():
    """Load configuration with robust repo-relative discovery.

    Search order for config.json:
      1) RHINOLEADERTOOL_CONFIG env var (absolute file path)
      2) Next to this script (__file__)
      3) Current working directory
      4) Legacy default under ~/source/repos/work/library/RhinoLeaderTool/config.json

    Also ensure a sensible base_path exists (defaults to the script directory
    when not explicitly provided), so other functions can locate CSVs and
    preset files within the cloned repository.
    """
    user_dir = os.path.expanduser("~")
    legacy_base = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")
    script_dir = os.path.dirname(os.path.abspath(__file__))

    candidates = []
    try:
        env_path = os.environ.get("RHINOLEADERTOOL_CONFIG")
        if env_path:
            candidates.append(env_path)
    except Exception:
        pass
    candidates.append(os.path.join(script_dir, "config.json"))
    candidates.append(os.path.join(os.getcwd(), "config.json"))
    candidates.append(os.path.join(legacy_base, "config.json"))

    cfg_path = None
    for path in candidates:
        try:
            if path and os.path.isfile(path):
                cfg_path = path
                break
        except Exception:
            continue

    default = {
        "logging": {"mode": "xlsx"},
        "export": {
            "target_styles": [
                "Standard 1:10 Rahmenbeschriftung",
                "Standard 1:10 Rahmenbeschriftung WHG Eingang",
                "Standard 1:10 Zargenbeschriftung",
                "Standard 1:10 Schiebetürbeschriftung",
                "Standard 1:10 Spez.Rahmenbeschriftung"
            ],
            "na_value": "NA",
            "floor_sort": True
        }
    }

    try:
        if cfg_path:
            with open(cfg_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            for k, v in file_cfg.items():
                default[k] = v
    except Exception:
        pass

    # Guarantee a valid base_path pointing to the repository when possible
    try:
        if not default.get("base_path"):
            default["base_path"] = script_dir
    except Exception:
        pass
    return default


def get_base_path(cfg):
    user_dir = os.path.expanduser("~")
    default_base = os.path.join(user_dir, "source", "repos", "work", "library", "RhinoLeaderTool")
    cfg_base = cfg.get("base_path") if isinstance(cfg, dict) else None
    if cfg_base and os.path.isdir(cfg_base):
        return cfg_base
    # Prefer repository directory (where this script lives) if present
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(script_dir):
            return script_dir
    except Exception:
        pass
    return default_base



