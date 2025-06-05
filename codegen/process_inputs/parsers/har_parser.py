import json

def parse_har(har_raw):
    har = json.loads(har_raw)
    entries = har.get("log", {}).get("entries", [])
    xhr_requests = []
    for entry in entries:
        try:
            # Only include XHR/fetch requests
            if entry.get("_resourceType") not in ("xhr", "fetch"):
                continue

            request = entry.get("request", {})
            response = entry.get("response", {})
            content = response.get("content", {})

            # Extract request headers, params, and body
            headers = {h["name"]: h["value"] for h in request.get("headers", [])}
            url = request.get("url", "")
            method = request.get("method", "")
            query_params = {q["name"]: q["value"] for q in request.get("queryString", [])}
            post_data = request.get("postData", {}).get("text", None)

            # Extract response body and status
            status = response.get("status")
            mime_type = content.get("mimeType", "")
            response_body = content.get("text", None) if mime_type.startswith("application/json") else None

            xhr_requests.append({
                "url": url,
                "method": method,
                "headers": headers,
                "query_params": query_params,
                "request_body": post_data,
                "response_status": status,
                "response_body": response_body,
            })
        except Exception:
            continue
    return xhr_requests