import json

def parse_har(har_raw):
    har = json.loads(har_raw)
    entries = har.get("log", {}).get("entries", [])
    json_bodies = []
    for entry in entries:
        try:
            content = entry["response"].get("content", {})
            if content.get("mimeType", "").startswith("application/json"):
                text = content.get("text")
                if text:
                    json_bodies.append({
                        "url": entry.get("request", {}).get("url", ""),
                        "json": json.loads(text)
                    })
        except Exception:
            continue
    return json_bodies