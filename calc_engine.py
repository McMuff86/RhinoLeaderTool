from write_leaders_to_file import (
    _normalize_key,
    _normalize_int_from_string,
    _get_user_value,
    load_elkuch_mapping,
    _is_override_bandmass_enabled,
)


def apply_bandmass_rules(leaders, cfg):
    # thin wrapper to call existing engine
    from write_leaders_to_file import autofill_band_masses_for_export
    return autofill_band_masses_for_export(leaders, cfg)


