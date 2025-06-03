import re
import json
import os

def extract_usage_type(call_code):
    """
    Returns the Playwright method chain, ignoring the last action if it is an action.
    Examples:
      page.getByTestId(locators.loc1).filter({ hasText: locators.loc3}).click() -> chained:getByTestId.filter
      page.locator(locators.username).fill(username) -> locator
      page.getByRole('button') -> getByRole
    """
    ACTION_METHODS = {"click", "fill", "type", "check", "uncheck", "selectOption", "isVisible", "textContent", "waitFor", "goto"}
    if call_code.startswith("page."):
        chain = call_code[5:]
        methods = [m.split("(", 1)[0] for m in chain.split(".") if "(" in m]
        # Remove last method if it's an action and there are at least two methods
        if methods and methods[-1] in ACTION_METHODS and len(methods) > 1:
            methods = methods[:-1]
        if len(methods) > 1:
            return "chained:" + ".".join(methods)
        elif methods:
            return methods[0]
    return "unknown"

def build_final_locator_chunks(locators, page_actions, class_name):
    value_to_key = {v: k for k, v in locators.items()}
    locator_chunks = {}

    # Regex for locators.<key> or locators['key'] or locators["key"]
    locators_pattern = re.compile(
        r"([a-zA-Z0-9_]*locators)\s*(?:\.([a-zA-Z0-9_]+)|\[\s*['\"]([a-zA-Z0-9_]+)['\"]\s*\])",
        re.IGNORECASE
    )
    # Regex for any string literal (for direct selectors)
    string_selector_pattern = re.compile(r"['\"]([^'\"]+)['\"]")

    # First pass: collect all usages by usage_type
    usage_map = {}  # (chunk_key, usage_type) -> list of usages

    for action in page_actions:
        code = action.get("code", "")
        line = action.get("line")
        usage_type = extract_usage_type(code)

        # Locators.<key> usages
        for match in locators_pattern.finditer(code):
            locator_map_name = match.group(1)
            key = match.group(2) or match.group(3)
            if locator_map_name and locator_map_name.lower().endswith("locators"):
                value = locators.get(key)
                if value:
                    chunk_key = f"{class_name}.{locator_map_name}.{key}"
                    usage_map.setdefault((chunk_key, usage_type), {
                        "type": usage_type,
                        "class_name": class_name,
                        "locator_key": key,
                        "locator_value": value,
                        "usages": []
                    })
                    usage_map[(chunk_key, usage_type)]["usages"].append({
                        "code": code,
                        "line": line
                    })

        # Direct selector usage (not in locators map)
        for match in string_selector_pattern.finditer(code):
            selector = match.group(1)
            if selector not in value_to_key:
                chunk_key = f"{class_name}.selector:{selector}"
                usage_map.setdefault((chunk_key, usage_type), {
                    "type": usage_type,
                    "class_name": class_name,
                    "locator_key": None,
                    "locator_value": selector,
                    "usages": []
                })
                usage_map[(chunk_key, usage_type)]["usages"].append({
                    "code": code,
                    "line": line
                })

    # Add locators that are defined but never used in page_actions (with type "unused")
    for key, value in locators.items():
        chunk_key = f"{class_name}.locators.{key}"
        if not any(chunk_key == k[0] for k in usage_map.keys()):
            usage_map[(chunk_key, "unused")] = {
                "type": "unused",
                "class_name": class_name,
                "locator_key": key,
                "locator_value": value,
                "usages": []
            }

    # Deduplicate usages for each locator chunk
    final_chunks = []
    for chunk in usage_map.values():
        seen = set()
        deduped_usages = []
        for usage in chunk["usages"]:
            key = (usage["code"], usage["line"])
            if key not in seen:
                seen.add(key)
                deduped_usages.append(usage)
        chunk["usages"] = deduped_usages
        final_chunks.append(chunk)

    return final_chunks

# --- Run for all PageObject JSON files ---
scan_split_dir = "scanner/scan_split"
output_path = "scanner/RAG/locator_chunks.jsonl"

ALLOWED_TYPES = {
    "locator",
    "getByTestId",
    "getByRole",
    "getByText",
    "filter",
    "nth",
    "first",
    "last"
    # Add any other types you want to allow
}

def is_allowed_type(chunk_type):
    if chunk_type in ALLOWED_TYPES:
        return True
    if chunk_type.startswith("chained:"):
        # chained:getByTestId.filter, chained:locator, etc.
        first = chunk_type[len("chained:"):].split(".", 1)[0]
        return first in ALLOWED_TYPES
    return False

with open(output_path, "w") as out:
    for fname in os.listdir(scan_split_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(scan_split_dir, fname)
        with open(fpath) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            continue
        locators_raw = data.get("locators", {})
        # Support both list and dict formats for locators
        if isinstance(locators_raw, list):
            locators = {loc["name"]: loc.get("value") for loc in locators_raw if "name" in loc and "value" in loc}
        else:
            locators = locators_raw
        page_actions = data.get("page_actions", [])
        # Use filename (without .json) as class name
        class_name = fname.replace(".json", "")
        chunks = build_final_locator_chunks(locators, page_actions, class_name)
        for chunk in chunks:
            if not is_allowed_type(chunk["type"]):
                continue
            out.write(json.dumps(chunk) + "\n")