import json
import os
import glob

def load_method_index(scan_dir):
    """Build a method index: { 'Class.method': True } for fast lookup."""
    index = {}
    for file in glob.glob(os.path.join(scan_dir, "*.json")):
        basename = os.path.basename(file)
        if basename.startswith("all_") or basename == "PageObjects.json":
            continue
        class_name = basename.replace(".json", "")
        with open(file) as f:
            data = json.load(f)
            for func in data.get("functions", []):
                method = func.get("method")
                if class_name and method:
                    key = f"{class_name}.{method}"
                    index[key] = True
    return index

def resolve_method_ref(class_name, method, method_index, parent_classes):
    """Find the method ref in index, walking up parent classes if needed."""
    checked = set()
    while class_name and class_name not in checked:
        checked.add(class_name)
        ref = f"{class_name}.{method}"
        if ref in method_index:
            return ref
        class_name = parent_classes.get(class_name)
        
    return None

def get_links():
    scan_dir = "scanner/scan_split"
    step_defs_path = os.path.join(scan_dir, "all_step_definitions.json")
    output_path = os.path.join(scan_dir, "all_step_definitions_linked.json")

    # Build method index for fast lookup
    method_index = load_method_index(scan_dir)

    # Load parent class map
    with open(os.path.join(scan_dir, "all_class_parents.json")) as f:
        class_parents = json.load(f)

    # Load all_step_definitions.json
    with open(step_defs_path) as f:
        all_steps = json.load(f)

    # Link step calls to method reference keys (with parent fallback)
    for step in all_steps:
        for call in step.get("calls", []):
            if call.get("object") == "pageObjects" and "." in call["method"]:
                page_obj, method = call["method"].split(".", 1)
                method_ref = resolve_method_ref(page_obj, method, method_index, class_parents)
                call["method_link"] = method_ref
            else:
                call["method_link"] = None

    # Save the enriched step definitions (with only method reference keys)
    with open(output_path, "w") as f:
        json.dump(all_steps, f, indent=2)
    print(f"[LINK] Step calls now reference method keys only: {output_path}")
