import json
import os
from pathlib import Path

mapping = {
  "loginPage": "samples/pageObjects/loginPage.ts",
  "dashboardPage": "samples/pageObjects/dashboardPage.ts"
}


def load_scan_output(path):
    with open(path) as f:
        return json.load(f)

def load_json_file(json_path):
    try:
        with open(json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load JSON file {json_path}: {e}")
        return {}

def resolve_test_data_links(references, source_file, base_dir):
    resolved_links = []
    for ref in references:
        raw_path = ref.get("file")
        abs_path = os.path.normpath(os.path.join(base_dir, raw_path))
        accessed_keys = ref.get("accessed_keys", [])

        found_keys = []
        json_data = load_json_file(abs_path)

        for key in accessed_keys:
            if key in json_data:
                found_keys.append(key)

        resolved_links.append({
            "source_file": source_file,
            "json_file": abs_path,
            "variable": ref["variable"],
            "line": ref["line"],
            "used_keys": accessed_keys,
            "found_keys": found_keys
        })

    return resolved_links

def link_steps(scan_output, base_dir):
    step_definitions = scan_output["step_definitions"]
    all_function_blocks = scan_output["functions"]

    # File-level function + reference info
    functions_by_file = {
        entry["path"]: {
            "functions": entry.get("functions", []),
            "test_data_references": entry.get("test_data_references", [])
        }
        for entry in all_function_blocks
    }

    # Heuristic: map objects to files
    object_to_file_map = {}
    for file_path, data in functions_by_file.items():
        for func in data["functions"]:
            obj = func.get("object")
            if obj and obj not in object_to_file_map:
                object_to_file_map[obj] = file_path

    # Manual override (this is required for cases like `loginPage`)
    manual_object_to_file_map = {
        "loginPage": "samples/pageObjects/loginPage.ts"
    }
    object_to_file_map.update(manual_object_to_file_map)

    linked = {}

    for step_def_file in step_definitions:
        file_path = step_def_file["path"]
        step_file_functions = functions_by_file.get(file_path, {}).get("functions", [])

        for step in step_def_file["steps"]:
            step_text = step["expression"]
            step_line = int(step["location"].split(":")[1])

            # Find all function calls after step definition
            linked_calls = [
                func for func in step_file_functions
                if func["line"] >= step_line
            ]

            # Extract used object names
            used_objects = set(func.get("object") for func in linked_calls if func.get("object"))

            # Resolve test data references from objects' source files
            test_data_references = []
            seen = set()
            for obj in used_objects:
                source_file = object_to_file_map.get(obj)
                if not source_file:
                    continue

                refs = functions_by_file.get(source_file, {}).get("test_data_references", [])
                resolved_refs = resolve_test_data_links(refs, source_file, base_dir)

                for ref in resolved_refs:
                    key = (ref["variable"], ref["json_file"], ref["line"])
                    if key not in seen:
                        test_data_references.append(ref)
                        seen.add(key)

            linked.setdefault(step_text, []).append({
                "step_location": step["location"],
                "linked_calls": linked_calls,
                "test_data_references": test_data_references
            })

    return linked


def main():
    scan_data = load_scan_output("scan_output.json")
    base_dir = os.getcwd()

    linked_steps = link_steps(scan_data, base_dir)
    output = {
        "linked_steps": linked_steps
    }

    with open("link_output.json", "w") as f:
        json.dump(output, f, indent=2)

    print("✅ Linked output written to link_output.json")

if __name__ == "__main__":
    main()
