
from tree_sitter import Parser, Language
from tree_sitter_typescript import language_typescript

from ast_utils import find_class_declarations, get_node_text
from extractors.class_info import extract_locators_map

TS_LANGUAGE = Language(language_typescript())
parser = Parser(language=TS_LANGUAGE)

PAGE_ACTION_PREFIXES = (
    "page.getBy",
    "page.locator",
    "page.waitFor",
    "page.goto",
    "page.click",
    "page.fill",
    "page.type",
    "page.check",
    "page.uncheck",
    "page.selectOption",
    "page.waitForSelector",
    "page.waitForResponse",
    "page.waitForLoadState",
    # Add more as needed
)

def extract_function_calls_and_data(tree, code, filepath, class_parents, page_class_name=None):
    root = tree.root_node
    function_calls = []
    locators_map = {}
    page_actions = []

    def get_params(params_node):
        params = []
        if params_node:
            for param in params_node.named_children:
                params.append(get_node_text(code, param))
        return params

    def add_function( func_name, class_name, parent_class, params, code_text, line):
        function_calls.append({
            "method": func_name,
            "class_name": class_name,
            "parent_class": parent_class,
            "filepath": filepath,
            "line": line,
            "params": params,
            "code": code_text
        })

    def walk(node, ancestors=[], visited=set(), current_class=None, parent_class=None, inside_class=False):
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
                walk(child, ancestors + [node], visited, class_name, parent_class, inside_class=True)
            return

        # --- Method definition or standalone function ---
        if node.type in ("method_definition", "function_declaration"):
            name_node = node.child_by_field_name("name")
            func_name = get_node_text(code, name_node) if name_node else "<anonymous>"
            params_node = node.child_by_field_name("parameters")
            params = get_params(params_node) if params_node else []
            line = node.start_point[0] + 1
            code_text = get_node_text(code, node)
            # For standalone functions, only add if not inside a class or if page_class_name matches
            if node.type == "function_declaration" and not inside_class:
                if page_class_name and filepath.lower().endswith(f"{page_class_name.lower()}.ts"):
                    add_function(func_name, page_class_name, None, params, code_text, line)
            else:
                add_function(func_name, current_class, parent_class, params, code_text, line)
            if func_name in visited:
                return
            visited.add(func_name)
            for child in node.children:
                walk(child, ancestors + [node], visited, current_class, parent_class, inside_class)
            visited.remove(func_name)
            
            
        if node.type == "call_expression":
            callee = node.child_by_field_name("function")
            callee_text = get_node_text(code, callee) if callee else ""
            code_text = get_node_text(code, node)
            if callee_text.startswith(PAGE_ACTION_PREFIXES):
                line = node.start_point[0] + 1
                page_actions.append({
                    "call": callee_text,
                    "class_name": current_class,
                    "filepath": filepath,
                    "line": line,
                    "code": code_text
                })

        # --- Recurse ---
        for child in node.children:
            walk(child, ancestors + [node], visited, current_class, parent_class, inside_class)

    page_class_name_detected = None
    class_nodes = find_class_declarations(root)
    for node in class_nodes:
        name_node = node.child_by_field_name("name")
        if name_node:
            page_class_name_detected = get_node_text(code, name_node)
            break

    walk(root, current_class=page_class_name or page_class_name_detected)
    return function_calls, locators_map, page_actions



def extract_step_definitions(code, filepath):
    import re
    step_keywords = ("Given", "When", "Then", "And", "But")
    pattern = re.compile(r"\b(" + "|".join(step_keywords) + r")\s*\((['\"`])(.+?)\2")
    step_definitions = []

    # Map line numbers to (keyword, expression)
    line_map = {}
    for i, line in enumerate(code.decode().splitlines()):
        match = pattern.search(line)
        if match:
            keyword, _, expression = match.groups()
            line_map[i + 1] = (keyword, expression)

    tree = parser.parse(code)
    root = tree.root_node

    def get_node_text(code, node):
        return code[node.start_byte:node.end_byte].decode()

    def get_params(params_node):
        params = []
        if params_node:
            for param in params_node.named_children:
                params.append(get_node_text(code, param))
        return params

    for node in root.children:
        if node.type == "expression_statement" and node.child_count > 0:
            call = node.children[0]
            if call.type == "call_expression":
                callee = call.child_by_field_name("function")
                if callee:
                    callee_text = get_node_text(code, callee)
                    if callee_text in step_keywords:
                        args = call.child_by_field_name("arguments")
                        if args and args.named_child_count >= 2:
                            expr_node = args.named_children[0]
                            func_node = args.named_children[1]
                            if expr_node.type in ("string", "template_string"):
                                expression = get_node_text(code, expr_node).strip('`"\'')
                                code_text = ""
                                params = []
                                if func_node.type in ("arrow_function", "function_expression"):
                                    params_node = func_node.child_by_field_name("parameters")
                                    params = get_params(params_node)
                                    code_text = get_node_text(code, func_node)
                                    line = func_node.start_point[0] + 1
                                else:
                                    line = node.start_point[0] + 1
                                step_definitions.append({
                                    "step_keyword": callee_text,
                                    "expression": expression,
                                    "location": f"{filepath}:{line}",
                                    "code": code_text,
                                    "params": params
                                })

    found_lines = {int(sd["location"].split(":")[1]) for sd in step_definitions}
    for line, (keyword, expression) in line_map.items():
        if line not in found_lines:
            step_definitions.append({
                "step_keyword": keyword,
                "expression": expression,
                "location": f"{filepath}:{line}",
                "code": "",
                "params": []
            })

    return {
        "steps": step_definitions
    }