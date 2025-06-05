import json
import os
import glob

def build_index():
    scan_dir = "codegen/output"
    method_index = {}
    for file in glob.glob(os.path.join(scan_dir, "*.json")):
        basename = os.path.basename(file)
        if basename.startswith("all_") or basename == "PageObjects.json":
            continue
        class_name = basename.replace(".json", "")
        with open(file) as f:
            data = json.load(f)
            for func in data.get("functions", []):
                method = func.get("method")
                # --- Add code extraction here ---
                # --- End code extraction ---
                if class_name and method:
                    key = f"{class_name}.{method}"
                    method_index[key] = {
                        "file": basename,
                        "class_name": class_name,
                        "method": method,
                        "details": func
                    }
    # Save the index
    with open(os.path.join(scan_dir, "method_index.json"), "w") as f:
        json.dump(method_index, f, indent=2)
    print("[INDEX] method_index.json written.")