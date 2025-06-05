
import os
import json

from extractors.step_defs import extract_step_definitions

def scan_step_definitions(step_def_dir, output_dir="codegen/output"):
    """
    Scans only the step definitions directory for step definitions and writes them to all_step_definitions.json.
    Also writes all methods defined in each step definition file to all_step_methods.json.
    """
    all_step_defs = []

    for root, _, files in os.walk(step_def_dir):
        for file in files:
            if file.endswith(".ts"):
                path = os.path.join(root, file)
                with open(path, "rb") as f:
                    code = f.read()
                    
                step_info = extract_step_definitions(code, path)
                if step_info["steps"]:
                    all_step_defs.extend(step_info["steps"])
               

    if all_step_defs:
        with open(os.path.join(output_dir, "all_step_definitions.json"), "w") as f:
            json.dump(all_step_defs, f, indent=2)
        print(f"[WRITE] all_step_definitions.json written from {step_def_dir}.")
    else:
        print(f"[INFO] No step definitions found in {step_def_dir}.")
  
   