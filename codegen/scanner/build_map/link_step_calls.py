import json
import os

from ast_utils import extract_code_from_file

def resolve_method_ref(class_name, method, method_index, parent_classes):
    checked = set()
    while class_name and class_name not in checked:
        checked.add(class_name)
        ref = f"{class_name}.{method}"
        if ref in method_index:
            return ref
        class_name = parent_classes.get(class_name)
    return None

def get_links():
    scan_dir = "codegen/output"
    step_defs_path = os.path.join(scan_dir, "all_step_definitions.json")
    output_path = os.path.join(scan_dir, "all_step_definitions_linked.json")

    # Load rich method index (with code and metadata)
    with open(os.path.join(scan_dir, "method_index.json")) as f:
        method_index = json.load(f)

    # Load parent class map
    with open(os.path.join(scan_dir, "all_class_parents.json")) as f:
        class_parents = json.load(f)

    # Load all_step_definitions.json
    with open(step_defs_path) as f:
        all_steps = json.load(f)

    for step in all_steps:
        # No need to extract code here; it's already present in step["code"]

        # Link step calls to method reference keys (with parent fallback)
        for call in step.get("calls", []):
            if call.get("object") == "pageObjects" and "." in call["method"]:
                page_obj, method = call["method"].split(".", 1)
                method_ref = resolve_method_ref(page_obj, method, method_index, class_parents)
                call["method_link"] = method_ref
                # Enrich with method code if found
                if method_ref and method_ref in method_index:
                    call["method_code"] = method_index[method_ref].get("code", "")
            else:
                call["method_link"] = None
                call["method_code"] = ""

    # Save the enriched step definitions (with method_code)
    with open(output_path, "w") as f:
        json.dump(all_steps, f, indent=2)
    print(f"[LINK] Step calls now reference method keys and include code: {output_path}")