import difflib

def flatten_json(y, prefix=''):
    out = {}
    if isinstance(y, dict):
        for k, v in y.items():
            out.update(flatten_json(v, f"{prefix}{k}." if prefix else k + "."))
    elif isinstance(y, list):
        for i, v in enumerate(y):
            out.update(flatten_json(v, f"{prefix}[{i}]."))
    else:
        out[prefix[:-1]] = y
    return out

def advanced_map_api_to_dom(api_data, ui_data, api_keyword=None, dom_keyword=None, max_fields=10):
    matched_api = next((entry for entry in api_data if api_keyword in entry["url"]), None) if api_keyword else (api_data[0] if api_data else None)
    flat_api = flatten_json(matched_api["json"]) if matched_api else {}
    mapping = []
    for k, v in list(flat_api.items())[:max_fields]:
        dom_match = next((node for node in ui_data if str(v) in node["text"]), None)
        if not dom_match and v:
            best = None
            best_score = 0.0
            for node in ui_data:
                score = difflib.SequenceMatcher(None, str(v), node["text"]).ratio()
                if score > best_score:
                    best_score = score
                    best = node
            if best_score > 0.6:
                dom_match = best
        mapping.append({
            "api_field": k,
            "api_value": v,
            "dom_text": dom_match["text"] if dom_match else "",
            "dom_html": dom_match["html"] if dom_match else "",
            "match_type": "fuzzy" if dom_match and str(v) not in dom_match["text"] else "exact" if dom_match else "none"
        })
    return {
        "api_url": matched_api["url"] if matched_api else api_keyword,
        "api_fields": list(flat_api.items())[:max_fields],
        "dom_keyword": dom_keyword,
        "mapping": mapping
    }