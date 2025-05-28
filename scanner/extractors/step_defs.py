

from scanner.ast_utils import extract_control_flow, get_node_text
import os
import json
import re
from tree_sitter import Parser, Language
from tree_sitter_typescript import language_typescript

TS_LANGUAGE = Language(language_typescript())
parser = Parser(language=TS_LANGUAGE)

def extract_methods_in_file(code, tree, filepath):
    """
    Extracts all top-level function and arrow function definitions in a file.
    Returns a list of dicts with name, location, and parameters.
    """
    methods = []
    root = tree.root_node

    def walk(node):
        # Top-level function declarations
        if node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            func_name = get_node_text(code, name_node) if name_node else "<anonymous>"
            line = node.start_point[0] + 1
            params = []
            params_node = node.child_by_field_name("parameters")
            if params_node:
                for param in params_node.named_children:
                    params.append(get_node_text(code, param))
            methods.append({
                "name": func_name,
                "location": f"{filepath}:{line}",
                "parameters": params
            })
        # Top-level variable declarations with arrow functions
        elif node.type == "lexical_declaration":
            for decl in node.named_children:
                if decl.type == "variable_declarator":
                    var_name_node = decl.child_by_field_name("name")
                    value_node = decl.child_by_field_name("value")
                    if value_node and value_node.type == "arrow_function":
                        func_name = get_node_text(code, var_name_node) if var_name_node else "<anonymous>"
                        line = decl.start_point[0] + 1
                        params = []
                        params_node = value_node.child_by_field_name("parameters")
                        if params_node:
                            for param in params_node.named_children:
                                params.append(get_node_text(code, param))
                        methods.append({
                            "name": func_name,
                            "location": f"{filepath}:{line}",
                            "parameters": params
                        })
        # Only walk top-level
        for child in node.children:
            if node.type == "program":
                walk(child)
    walk(root)
    return methods





def extract_step_definitions(code, filepath):
    """
    Extracts step definitions and their implementation methods from a step-def file.
    """
    step_keywords = ("Given", "When", "Then", "And", "But")
    pattern = re.compile(r"\b(" + "|".join(step_keywords) + r")\s*\((['\"`])(.+?)\2")
    step_definitions = []
    methods = []

    # For mapping expressions to lines (for fallback)
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
            params = []
            if node.type == "call_expression":
               
                callee = node.child_by_field_name("function")
                args = node.child_by_field_name("arguments")
                if args:
                     for arg in args.named_children:
                        params.append(get_node_text(code, arg))
                if callee:
                    callee_text = get_node_text(code, callee)
                    if "." in callee_text:
                        obj, method = callee_text.split(".", 1)
                    else:
                        obj, method = None, callee_text
                    control_flow =  extract_control_flow(func_node, code)
                    control_flow = control_flow if control_flow else []
                    line = node.start_point[0] + 1  
                    calls.append({"object": obj, "method": method, "args": params,"control_flow": control_flow, "line":line})

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
                step_fn = get_node_text(code, callee) if callee else None
               
               
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
                                "step_function": step_fn,
                                "expression": expression,
                                "location": f"{filepath}:{line}",
                                "calls": calls,
                                "params":params
                            })

    # Fallback for regex-only matches
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



