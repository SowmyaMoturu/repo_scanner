import os
import json
import re
from tree_sitter import Parser, Language
from tree_sitter_typescript import language_typescript

from scanner.ast_utils import extract_control_flow, find_class_declarations, get_node_text
from scanner.extractors.class_info import extract_class_inheritance, extract_locators_map

TS_LANGUAGE = Language(language_typescript())
parser = Parser(language=TS_LANGUAGE)

def extract_test_data(node, code, filepath, ancestors, imported_vars):
    refs = []
    enclosing_func = None
    if node.type == "member_expression":
        object_node = node.child_by_field_name("object")
        property_node = node.child_by_field_name("property")
        if object_node and property_node:
            obj = object_node.text.decode()
            prop = property_node.text.decode()
            if obj == "world":
                parent = ancestors[-1] if ancestors else None
                if parent and parent.type == "assignment_expression":
                    for anc in reversed(ancestors):
                        if anc.type in ("function_declaration", "method_definition"):
                            name_node = anc.child_by_field_name("name")
                            if name_node:
                                enclosing_func = name_node.text.decode()
                                break
                    refs.append({
                        "variable": "world",
                        "property": prop,
                        "access": "set",
                        "line": parent.start_point[0] + 1,
                        "filepath": filepath,
                        "enclosing_function": enclosing_func
                    })
                else:
                    refs.append({
                        "variable": "world",
                        "property": prop,
                        "access": "get",
                        "line": node.start_point[0] + 1,
                        "filepath": filepath,
                        "enclosing_function": enclosing_func
                    })
    if node.type == "call_expression":
        callee = node.child_by_field_name("function")
        if callee and callee.type == "import":
            arg_node = node.child_by_field_name("arguments")
            if arg_node and len(arg_node.named_children) > 0:
                arg = arg_node.named_children[0]
                if arg.type in ["template_string", "string"]:
                    imported_path = arg.text.decode().strip('"\'`')
                    declarator = None
                    for anc in reversed(ancestors):
                        if anc.type == "variable_declarator":
                            declarator = anc
                            break
                    if declarator:
                        var_node = declarator.child_by_field_name("name")
                        if var_node:
                            var_name = var_node.text.decode()
                            imported_vars[var_name] = imported_path
                            refs.append({
                                "variable": var_name,
                                "file": imported_path,
                                "line": node.start_point[0] + 1,
                                "accessed_keys": [],
                                "filepath": filepath,
                                "enclosing_function": enclosing_func
                            })
    return refs

def extract_function_calls_and_data(tree, code, filepath, class_parents, page_class_name=None):
    root = tree.root_node
    function_calls = []
    imported_vars = {}
    test_data_references = []
    locators_map = {}
    methods = []
    
    def get_params(params_node):
        params = []
        if params_node:
            for param in params_node.named_children:
                params.append(get_node_text(code, param))
        return params

    def walk(node, ancestors=[], call_chain=[], visited=set(), current_class=None, parent_class=None, inside_class=False):
        # --- Class context ---
        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            class_name = get_node_text(code, name_node) if name_node else None
            super_node = node.child_by_field_name("superclass")
            parent_class = get_node_text(code, super_node) if super_node else None
            class_locators = extract_locators_map(code)
            if class_locators:
                locators_map.update(class_locators)
            for child in node.children:
                walk(child, ancestors + [node], call_chain, visited, class_name, parent_class, inside_class=True)
            return

        # --- Method definition ---
        if node.type == "method_definition":
            name_node = node.child_by_field_name("name")
            func_name = get_node_text(code, name_node) if name_node else "<anonymous>"
            params_node = node.child_by_field_name("parameters")
            params = get_params(params_node) if params_node else []
            node_line = node.start_point[0] + 1
            method_dict = {
                "object": None,
                "method": func_name,
                "class_name": current_class,
                "parent_class": parent_class,
                "enclosing_function": None,
                "filepath": filepath,
                "line": node_line,
                "call_chain": call_chain[:],
                "params": params
            }
            control_flow = extract_control_flow(node, code)
            if control_flow:
                    method_dict["control_flow"] = control_flow
            function_calls.append(method_dict)
            methods.append(method_dict)
            if func_name in visited:
                return
            visited.add(func_name)
            new_chain = call_chain + [(filepath, func_name)]
            for child in node.children:
                walk(child, ancestors + [node], new_chain, visited, current_class, parent_class, inside_class)
            visited.remove(func_name)
            return

        # --- Standalone function ---
        if node.type == "function_declaration" and not inside_class:
            name_node = node.child_by_field_name("name")
            func_name = get_node_text(code, name_node) if name_node else "<anonymous>"
            params_node = node.child_by_field_name("parameters")
            params = get_params(params_node) if params_node else []
            node_line = node.start_point[0] + 1
            
            if page_class_name and filepath.lower().endswith(f"{page_class_name.lower()}.ts"):
                method_dict = {
                    "object": None,
                    "method": func_name,
                    "class_name": page_class_name,
                    "parent_class": None,
                    "enclosing_function": None,
                    "filepath": filepath,
                    "line": node_line,
                    "call_chain": call_chain[:],
                    "params": params
                }
                control_flow = extract_control_flow(node, code)
                if control_flow:
                    method_dict["control_flow"] = control_flow
                function_calls.append(method_dict)
                methods.append(method_dict)
            if func_name in visited:
                return
            visited.add(func_name)
            new_chain = call_chain + [(filepath, func_name)]
            for child in node.children:
                walk(child, ancestors + [node], new_chain, visited, current_class, parent_class, inside_class)
            visited.remove(func_name)
            return

        # --- Function calls and browser actions ---
        if node.type == "call_expression":
            callee = node.child_by_field_name("function")
            args_node = node.child_by_field_name("arguments")
            args = []
            if args_node:
                for arg in args_node.named_children:
                    args.append(get_node_text(code, arg))
            if callee:
                text = get_node_text(code, callee)
                node_line = node.start_point[0] + 1
                enclosing_func = None
                for anc in reversed(ancestors):
                    if anc.type in ("function_declaration", "method_definition"):
                        name_node = anc.child_by_field_name("name")
                        if name_node:
                            enclosing_func = get_node_text(code, name_node)
                            break
                obj, method = None, None
                if "." in text:
                    obj, method = text.split(".", 1)
                else:
                    obj, method = text, None

                function_calls.append({
                    "object": obj,
                    "method": method,
                    "line": node_line,
                    "enclosing_function": enclosing_func,
                    "filepath": filepath,
                    "call_chain": call_chain[:],
                    "class_name": current_class,
                    "parent_class": parent_class,
                    "args": args
                })

        # --- Test data references ---
        test_data_references.extend(extract_test_data(node, code, filepath, ancestors, imported_vars))

        for child in node.children:
            walk(child, ancestors + [node], call_chain, visited, current_class, parent_class, inside_class)

    page_class_name_detected = None
    class_nodes = find_class_declarations(root)
    for node in class_nodes:
        name_node = node.child_by_field_name("name")
        if name_node:
            page_class_name_detected = get_node_text(code, name_node)
            break

    walk(root, current_class=page_class_name or page_class_name_detected)
    return function_calls, test_data_references, locators_map, page_class_name or page_class_name_detected

def extract_step_definitions(code, filepath):
    step_keywords = ("Given", "When", "Then", "And", "But")
    pattern = re.compile(r"\b(" + "|".join(step_keywords) + r")\s*\((['\"`])(.+?)\2")
    step_definitions = []
    methods = []

    line_map = {}
    for i, line in enumerate(code.decode().splitlines()):
        match = pattern.search(line)
        if match:
            _, _, expression = match.groups()
            line_map[i + 1] = expression

    tree = parser.parse(code)
    root = tree.root_node

    def get_params(params_node):
        params = []
        if params_node:
            for param in params_node.named_children:
                params.append(get_node_text(code, param))
        return params

    def get_calls_from_body(body_node):
        calls = []
        def walk(node):
            if node.type == "await_expression" and node.child_count > 0:
                walk(node.children[0])
            elif node.type == "call_expression":
                callee = node.child_by_field_name("function")
                args_node = node.child_by_field_name("arguments")
                args = []
                if args_node:
                    for arg in args_node.named_children:
                        args.append(get_node_text(code, arg))
                if callee:
                    callee_text = get_node_text(code, callee)
                    if "." in callee_text:
                        obj, method = callee_text.split(".", 1)
                    else:
                        obj, method = None, callee_text
                    calls.append({"object": obj, "method": method, "args": args})
                for child in node.children:
                    walk(child)
            else:
                for child in node.children:
                    walk(child)
        walk(body_node)
        return calls

    for node in root.children:
        if node.type == "expression_statement" and node.child_count > 0:
            call = node.children[0]
            if call.type == "call_expression":
                callee = call.child_by_field_name("function")
                if callee and get_node_text(code, callee) in step_keywords:
                    args = call.child_by_field_name("arguments")
                    if args and args.named_child_count >= 2:
                        expr_node = args.named_children[0]
                        func_node = args.named_children[1]
                        if expr_node.type in ("string", "template_string"):
                            expression = get_node_text(code, expr_node).strip('`"\'')
                            calls = []
                            if func_node.type in ("arrow_function", "function_expression"):
                                body = func_node.child_by_field_name("body")
                                if body:
                                    calls = get_calls_from_body(body)
                                params_node = func_node.child_by_field_name("parameters")
                                params = get_params(params_node)
                                line = func_node.start_point[0] + 1
                                methods.append({
                                    "name": "<anonymous>",
                                    "location": f"{filepath}:{line}",
                                    "parameters": params
                                })
                            line = node.start_point[0] + 1
                            step_definitions.append({
                                "expression": expression,
                                "location": f"{filepath}:{line}",
                                "calls": calls
                            })

    found_lines = {int(sd["location"].split(":")[1]) for sd in step_definitions}
    for line, expression in line_map.items():
        if line not in found_lines:
            step_definitions.append({
                "expression": expression,
                "location": f"{filepath}:{line}",
                "calls": []
            })

    return {
        "steps": step_definitions,
        "methods": methods
    }

def scan_step_definitions(step_def_dir, output_dir="scanner/scan_split"):
    all_step_defs = []
    all_step_methods = []
    for root, _, files in os.walk(step_def_dir):
        for file in files:
            if file.endswith(".ts"):
                path = os.path.join(root, file)
                with open(path, "rb") as f:
                    code = f.read()
                step_info = extract_step_definitions(code, path)
                if step_info["steps"]:
                    all_step_defs.extend(step_info["steps"])
                if step_info["methods"]:
                    all_step_methods.extend(step_info["methods"])
    if all_step_defs:
        with open(os.path.join(output_dir, "all_step_definitions.json"), "w") as f:
            json.dump(all_step_defs, f, indent=2)
        print(f"[WRITE] all_step_definitions.json written from {step_def_dir}.")
    else:
        print(f"[INFO] No step definitions found in {step_def_dir}.")
    if all_step_methods:
        with open(os.path.join(output_dir, "all_step_methods.json"), "w") as f:
            json.dump(all_step_methods, f, indent=2)
        print(f"[WRITE] all_step_methods.json written from {step_def_dir}.")
    else:
        print(f"[INFO] No step methods found in {step_def_dir}.")

def scan_multiple_directories(root_dirs, output_dir="scanner/scan_split"):
    os.makedirs(output_dir, exist_ok=True)
    all_class_parents = {}
    all_page_data = {}

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

    print("Scanning for page/API objects and capturing methods, locators, test data in multiple directories...")
    for root_dir in root_dirs:
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".ts"):
                    path = os.path.join(root, file)
                    with open(path, "rb") as f:
                        code = f.read()
                    tree = parser.parse(code)

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
                        continue

                    print(f"[PROCESS] Processing {page_class_name} ({file})...")

                    functions, test_data, locators_map, _ = extract_function_calls_and_data(
                        tree, code, path,  all_class_parents, page_class_name=page_class_name)

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

    for page_class_name, page_data in all_page_data.items():
        with open(os.path.join(output_dir, f"{page_class_name}.json"), "w") as pf:
            json.dump(page_data, pf, indent=2)
        print(f"[WRITE] {page_class_name}.json written.")

    print("✅ Modular scan complete. Output written to", output_dir)

if __name__ == "__main__":
    page_dirs = [
        "src/pages",
        "src/utils",
        "src/api.calls",
        "src/setup"
    ]
    scan_multiple_directories(page_dirs)
    scan_step_definitions("src/step-definitions")