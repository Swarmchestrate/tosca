def flatten(val):
    if isinstance(val, dict):
        if "$primitive" in val:
            return val["$primitive"]
        if "$list" in val:
            return [flatten(v) for v in val["$list"]]
        if "$map" in val:
            out = {}
            for pair in val["$map"]:
                key = flatten(pair.get("$key"))
                value = flatten(pair)
                out[key] = value
            return out
        return {k: flatten(v) for k, v in val.items()}
    return val


def extract_properties(prop_dict):
    extracted = {}
    for k, v in prop_dict.items():
        meta = v.get("$meta", {}) if isinstance(v, dict) else {}
        alias = meta.get("metadata", {}).get("alias")
        extracted_key = alias if alias else k
        extracted[extracted_key] = flatten(v)
    return extracted
