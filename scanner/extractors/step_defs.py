from scanner.ast_utils import get_node_text
import os
import json
import re
from tree_sitter import Parser, Language
from tree_sitter_typescript import language_typescript

TS_LANGUAGE = Language(language_typescript())
parser = Parser(language=TS_LANGUAGE)

def extract_step_definitions(code, filepath):
    """
    Extracts step definitions from a step-def file.
    Each step includes: step_keyword, expression, location, code, params, calls.
    """
    step_keywords = ("Given", "When", "Then", "And", "But")
    pattern = re.compile(r"\b(" + "|".join(step_keywords) + r")\s*\((['\"`])(.+?)\2")
    step_definitions = []

    # For mapping expressions to lines (for fallback)
    line_map = {}
    for i, line in enumerate(code.decode().splitlines()):
        match = pattern.search(line)
        if match:
            keyword, _, expression = match.groups()
            line_map[i + 1] = (keyword, expression)

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
                    line = node.start_point[0] + 1
                    calls.append({"object": obj, "method": method, "args": params, "line": line})
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
                                calls = []
                                if func_node.type in ("arrow_function", "function_expression"):
                                    params_node = func_node.child_by_field_name("parameters")
                                    params = get_params(params_node)
                                    code_text = get_node_text(code, func_node)
                                    body = func_node.child_by_field_name("body")
                                    if body:
                                        calls = get_calls_from_body(body)
                                    line = func_node.start_point[0] + 1
                                else:
                                    line = node.start_point[0] + 1
                                step_definitions.append({
                                    "step_keyword": callee_text,
                                    "expression": expression,
                                    "location": f"{filepath}:{line}",
                                    "calls": calls,
                                    "code": code_text,
                                    "params": params
                                })

    # Fallback for regex-only matches
    found_lines = {int(sd["location"].split(":")[1]) for sd in step_definitions}
    for line, (keyword, expression) in line_map.items():
        if line not in found_lines:
            step_definitions.append({
                "step_keyword": keyword,
                "expression": expression,
                "location": f"{filepath}:{line}",
                "calls": [],
                "code": "",
                "params": []
            })

    return {
        "steps": step_definitions
    }