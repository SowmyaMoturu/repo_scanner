import json

def parse_cdp_events(cdp_json):
    if isinstance(cdp_json, str):
        cdp_data = json.loads(cdp_json)
    else:
        cdp_data = cdp_json
    actions = []
    for entry in cdp_data.get("events", cdp_data):
        method = entry.get("method", "")
        params = entry.get("params", {})
        if method == "Input.dispatchMouseEvent":
            action = f"Mouse {params.get('type')} at ({params.get('x')}, {params.get('y')})"
            actions.append(action)
        elif method == "Input.dispatchKeyEvent":
            action = f"Key {params.get('type')} '{params.get('key')}'"
            actions.append(action)
        elif method == "Runtime.evaluate" and "expression" in params:
            actions.append(f"JS Eval: {params['expression'][:60]}...")
        elif method == "DOM.setAttributeValue":
            actions.append(f"Set attribute {params.get('name')} on node {params.get('nodeId')}")
        elif method == "Network.requestWillBeSent":
            url = params.get("request", {}).get("url", "")
            actions.append(f"API Request: {url}")
        elif method == "Network.responseReceived":
            url = params.get("response", {}).get("url", "")
            status = params.get("response", {}).get("status", "")
            actions.append(f"API Response: {url} (status {status})")
    summary = "CDP Session Actions:\n" + "\n".join(actions[:20])
    return summary