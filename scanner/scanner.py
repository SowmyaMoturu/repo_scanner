import os
import json
from tree_sitter import Parser, Language
from tree_sitter_typescript import language_typescript

TS_LANGUAGE = Language(language_typescript())
parser = Parser(language=TS_LANGUAGE)

def is_descendant(child, parent):
    if child == parent:
        return True
    for p_child in parent.children:
        if is_descendant(child, p_child):
            return True
    return False


def extract_function_calls(code, tree, filepath):
    root_node = tree.root_node
    calls = []
    test_data_references = []
    imported_vars = {}

    def extract_conditionals_with_branch(node, ancestors):
        conditionals = []
        for ancestor in ancestors:
            if ancestor.type == "if_statement":
                consequence = ancestor.child_by_field_name("consequence")
                alternative = ancestor.child_by_field_name("alternative")
                if consequence and is_descendant(node, consequence):
                    conditionals.append({"type": "if_statement", "branch": "consequent"})
                elif alternative and is_descendant(node, alternative):
                    conditionals.append({"type": "if_statement", "branch": "alternate"})
                else:
                    conditionals.append({"type": "if_statement", "branch": "unknown"})

            elif ancestor.type in ["ternary_expression", "conditional_expression"]:
                consequence = ancestor.child_by_field_name("consequence")
                alternative = ancestor.child_by_field_name("alternative")
                if consequence and is_descendant(node, consequence):
                    conditionals.append({"type": "ternary_expression", "branch": "consequent"})
                elif alternative and is_descendant(node, alternative):
                    conditionals.append({"type": "ternary_expression", "branch": "alternate"})
                else:
                    conditionals.append({"type": "ternary_expression", "branch": "unknown"})

            elif ancestor.type == "switch_statement":
                conditionals.append({"type": "switch_statement", "branch": "case_or_default"})

            elif ancestor.type.startswith("for") or ancestor.type in ["while_statement", "do_statement"]:
                conditionals.append({"type": ancestor.type, "branch": "loop"})

        return conditionals

    def walk(node, ancestors=[]):
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
                                test_data_references.append({
                                    "variable": var_name,
                                    "file": imported_path,
                                    "line": node.start_point[0] + 1,
                                    "accessed_keys": []
                                })
                                                               

            if callee:
                try:
                    method_text = code[callee.start_byte:callee.end_byte].decode("utf-8")
                except AttributeError:
                    method_text = code[callee.start_byte:callee.end_byte]
                if "." in method_text:
                    obj, method = method_text.split(".", 1)
                    calls.append({
                        "object": obj,
                        "method": method,
                        "line": node.start_point[0] + 1,
                        "conditionals": extract_conditionals_with_branch(node, ancestors)
                    })

                            # Detect: data[testdata]
        if node.type == "subscript_expression":
            print(node.type)
            object_node = node.child_by_field_name("object")
            index_node = node.child_by_field_name("index")

            if object_node and object_node.type == "identifier":
                var_name = object_node.text.decode()
                if var_name in imported_vars:
                    key = None
                    if index_node.type == "identifier":
                        key = index_node.text.decode()
                    elif index_node.type in ["string", "template_string"]:
                        key = index_node.text.decode().strip('"\'`')

                    if key:
                        for ref in test_data_references:
                            if ref["variable"] == var_name:
                                    ref.setdefault("accessed_keys", []).append(key)

        # Property access: world.my_data or similar
        if node.type == "member_expression":
            object_node = node.child_by_field_name("object")
            property_node = node.child_by_field_name("property")

            if object_node and property_node:
                obj = object_node.text.decode()
                prop = property_node.text.decode()

                if obj == "world":
                    parent = ancestors[-1] if ancestors else None

                    if parent and parent.type == "assignment_expression":
                        # This is a write: world.my_data = ...
                        test_data_references.append({
                            "variable": "world",
                            "property": prop,
                            "access": "set",
                            "line": parent.start_point[0] + 1,
                            "file": filepath
                        })
                    else:
                        # This is a read: data = world.my_data
                        test_data_references.append({
                            "variable": "world",
                            "property": prop,
                            "access": "get",
                            "line": node.start_point[0] + 1,
                            "file": filepath
                        })


        for child in node.children:
            walk(child, ancestors + [node])


    walk(root_node)
    return {
        "path": filepath,
        "functions": calls,
        "test_data_references": test_data_references
    }


def extract_step_definitions(code, tree, filepath):
    import re
    step_keywords = ["Given", "When", "Then"]
    pattern = re.compile(rf"\b({'|'.join(step_keywords)})\((['\"`])(.+?)\2")

    lines = code.decode("utf-8").split("\n")
    step_definitions = []

    for i, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            keyword, _, expression = match.groups()
            step_definitions.append({
                "expression": expression,
                "location": f"{filepath}:{i + 1}"
            })

    return {
        "path": filepath,
        "steps": step_definitions
    }


def scan_directory(directory):
    results = {
        "step_definitions": [],
        "functions": []
    }

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".ts"):
                filepath = os.path.join(root, file)
                with open(filepath, "rb") as f:
                    code = f.read()
                tree = parser.parse(code)

                step_defs = extract_step_definitions(code, tree, filepath)
                funcs = extract_function_calls(code, tree, filepath)

                if step_defs["steps"]:
                    results["step_definitions"].append(step_defs)
                if funcs["functions"]:
                    results["functions"].append(funcs)

    return results


if __name__ == "__main__":
    result = scan_directory("samples")
    with open("scan_output.json", "w") as f:
        json.dump(result, f, indent=2)
    print("✅ Scan complete. Output written to scan_output.json")
