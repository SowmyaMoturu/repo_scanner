
import os
import json
import re
from tree_sitter import Parser, Language
from tree_sitter_typescript import language_typescript

from scanner.ast_utils import get_node_text, find_class_declarations
from scanner.extractors.class_info import  extract_class_inheritance
from scanner.extractors.function_calls import extract_function_calls_and_data

TS_LANGUAGE = Language(language_typescript())
parser = Parser(language=TS_LANGUAGE)



def scan_multiple_directories(root_dirs, output_dir="scanner/scan_split"):
    """
    Scans multiple directories for page/API objects, merges results, and writes outputs once.
    """
    os.makedirs(output_dir, exist_ok=True)
    all_class_parents = {}
    all_page_data = {}

    # --- First pass: collect all class parents ---
    print("Scanning for class inheritance in multiple directories...")
    for root_dir in root_dirs:
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".ts"):
                    path = os.path.join(root, file)
                    with open(path, "rb") as f:
                        code = f.read()
                    tree = parser.parse(code)
                    class_parents = extract_class_inheritance(tree, code)
                    all_class_parents.update(class_parents)

    if all_class_parents:
        with open(os.path.join(output_dir, "all_class_parents.json"), "w") as f:
            json.dump(all_class_parents, f, indent=2)
        print(f"  Wrote class parents for {len(all_class_parents)} classes.")

    # --- Second pass: process page/API objects only ---
    print("Scanning for page/API objects and capturing methods, locators, test data in multiple directories...")
    for root_dir in root_dirs:
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".ts"):
                    path = os.path.join(root, file)
                    with open(path, "rb") as f:
                        code = f.read()
                    tree = parser.parse(code)

                    # Find main class name (page or API object)
                    page_class_name = None
                    class_nodes = find_class_declarations(tree.root_node)
                    for node in class_nodes:
                        name_node = node.child_by_field_name("name")
                        if name_node:
                            page_class_name = get_node_text(code, name_node)
                            print(f"[PAGE] Found class: {page_class_name} in {file}")
                            break

                    if not page_class_name:
                        print(f"[SKIP] {file}: No class declaration found.")
                        continue  # Only process files with a main class

                    print(f"[PROCESS] Processing {page_class_name} ({file})...")

                    # Functions, test data, locators
                    functions, test_data, locators_map, _ = extract_function_calls_and_data(
                        tree, code, path,  all_class_parents, page_class_name=page_class_name)

                    # Only write files if there is data
                    page_data = {}
                    if functions:
                        page_data["functions"] = functions
                    if locators_map:
                        page_data["locators"] = locators_map
                    if test_data:
                        page_data["test_data_references"] = test_data

                    if not page_data:
                        print(f"[SKIP] {file}: No functions, locators, or test data found for {page_class_name}.")
                        continue

                    all_page_data[page_class_name] = page_data

    # Write all page/API object files
    for page_class_name, page_data in all_page_data.items():
        with open(os.path.join(output_dir, f"{page_class_name}.json"), "w") as pf:
            json.dump(page_data, pf, indent=2)
        print(f"[WRITE] {page_class_name}.json written.")

    print("✅ Modular scan complete. Output written to", output_dir)


