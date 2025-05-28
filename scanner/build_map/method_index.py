import json
import os
import glob


def get_method_details(ref_list, index_path, scan_dir, parent_classes):
    """
    ref_list: list of method refs, e.g. ["LoginPage.goto", "BasePage.goto"]
    index_path: path to method_file_index.json
    scan_dir: directory containing page object JSONs
    parent_classes: dict mapping class_name -> parent_class_name
    """
    # Load the index
    with open(index_path) as f:
        index = json.load(f)

    # Group refs by file and class
    file_class_to_methods = {}
    ref_to_class_method = {}
    for ref in ref_list:
        entry = index.get(ref)
        if entry:
            file_class = (entry["file"], ref.split(".", 1)[0])
            file_class_to_methods.setdefault(file_class, []).append((ref, entry["method"]))
            ref_to_class_method[ref] = (ref.split(".", 1)[0], entry["method"])
        else:
            ref_to_class_method[ref] = (ref.split(".", 1)[0], ref.split(".", 1)[1])

    # Load each file once and collect results, checking parent classes if needed
    results = {}
    loaded_files = {}
    for (file, class_name), ref_methods in file_class_to_methods.items():
        file_path = os.path.join(scan_dir, file)
        if file_path not in loaded_files:
            try:
                with open(file_path) as f:
                    data = json.load(f)
                loaded_files[file_path] = data.get("functions", [])
            except Exception:
                loaded_files[file_path] = []
        methods = loaded_files[file_path]
        # Build a lookup for this class
        class_methods = {func.get("method"): func for func in methods if func.get("class_name") == class_name}
        for ref, method in ref_methods:
            # Try to find method in class or parent classes
            found = None
            checked = set()
            search_class = class_name
            while search_class and search_class not in checked:
                checked.add(search_class)
                found = next((func for func in methods if func.get("class_name") == search_class and func.get("method") == method), None)
                if found:
                    break
                search_class = parent_classes.get(search_class)
            results[ref] = found
    # For refs not in index, try to find in parent classes (if possible)
    for ref, (class_name, method) in ref_to_class_method.items():
        if ref not in results:
            found = None
            checked = set()
            search_class = class_name
            while search_class and search_class not in checked:
                checked.add(search_class)
                file_path = os.path.join(scan_dir, f"{search_class}.json")
                if os.path.exists(file_path):
                    if file_path not in loaded_files:
                        try:
                            with open(file_path) as f:
                                data = json.load(f)
                            loaded_files[file_path] = data.get("functions", [])
                        except Exception:
                            loaded_files[file_path] = []
                    methods = loaded_files[file_path]
                    found = next((func for func in methods if func.get("class_name") == search_class and func.get("method") == method), None)
                    if found:
                        break
                search_class = parent_classes.get(search_class)
            results[ref] = found
    return results

# Example usage:
# with open("scanner/scan_split/all_class_parents.json") as f:
#     parent_classes = json.load(f)
# refs = ["LoginPage.goto", "BasePage.goto"]
# details = get_method_details(refs, "scanner/scan_split/method_file_index.json", "scanner/scan_split", parent_classes)
# print(details)




def build_index():
    scan_dir = "scanner/scan_split"
    step_defs_path = os.path.join(scan_dir, "all_step_definitions.json")
    output_path = os.path.join(scan_dir, "all_step_definitions_linked.json")

    # Load all_step_definitions.json
    with open(step_defs_path) as f:
        all_steps = json.load(f)

    # Link step calls to method reference keys
    for step in all_steps:
        for call in step.get("calls", []):
            if call.get("object") == "pageObjects" and "." in call["method"]:
                page_obj, method = call["method"].split(".", 1)
                method_ref = f"{page_obj}.{method}"
                call["method_link"] = method_ref
            else:
                call["method_link"] = None

    # Save the enriched step definitions (with only method reference keys)
    with open(output_path, "w") as f:
        json.dump(all_steps, f, indent=2)
    print(f"[LINK] Step calls now reference method keys only: {output_path}")
