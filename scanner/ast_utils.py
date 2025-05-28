
def get_node_text(code, node):
    return code[node.start_byte:node.end_byte].decode()

def find_class_declarations(root):
    """
    Finds all class_declaration nodes, including those inside export_statement.
    """
    class_nodes = []
    for node in root.children:
        if node.type == "class_declaration":
            class_nodes.append(node)
        elif node.type == "export_statement":
            for child in node.children:
                if child.type == "class_declaration":
                    class_nodes.append(child)
    return class_nodes

def extract_control_flow(node, code, preview_chars=80):
    """
    Recursively extract control flow constructs from the AST node.
    Returns a list of dicts describing each control flow block,
    including line numbers and a short preview for each block.
    """
    control_flows = []

    def get_preview(n):
        text = code[n.start_byte:n.end_byte].decode()
        return text[:preview_chars].replace('\n', ' ') + ('...' if len(text) > preview_chars else '')

    def walk(n):
        if n.type in ("if_statement", "switch_statement", "ternary_expression",
                      "for_statement", "while_statement", "do_statement",
                      "for_in_statement", "for_of_statement"):
            flow = {
                "type": n.type,
                "start_line": n.start_point[0] + 1,
                "end_line": n.end_point[0] + 1,
                "preview": get_preview(n)
            }
            # --- If statement ---
            if n.type == "if_statement":
                cond = n.child_by_field_name("condition")
                flow["condition"] = get_preview(cond) if cond else None
                consequent = n.child_by_field_name("consequence")
                if consequent:
                    flow["consequent"] = {
                        "start_line": consequent.start_point[0] + 1,
                        "end_line": consequent.end_point[0] + 1,
                        "preview": get_preview(consequent)
                    }
                alternate = n.child_by_field_name("alternative")
                if alternate:
                    flow["alternate"] = {
                        "start_line": alternate.start_point[0] + 1,
                        "end_line": alternate.end_point[0] + 1,
                        "preview": get_preview(alternate)
                    }
            # --- Switch statement ---
            if n.type == "switch_statement":
                cond = n.child_by_field_name("value")
                flow["condition"] = get_preview(cond) if cond else None
                cases = []
                for child in n.children:
                    if child.type == "switch_case":
                        case_val = child.child_by_field_name("value")
                        case_body = child.child_by_field_name("body")
                        cases.append({
                            "case": get_preview(case_val) if case_val else "default",
                            "start_line": child.start_point[0] + 1,
                            "end_line": child.end_point[0] + 1,
                            "preview": get_preview(case_body) if case_body else ""
                        })
                flow["cases"] = cases
            # --- Loops ---
            if n.type in ("for_statement", "while_statement", "do_statement", "for_in_statement", "for_of_statement"):
                cond = n.child_by_field_name("condition")
                flow["condition"] = get_preview(cond) if cond else None
                body = n.child_by_field_name("body")
                if body:
                    flow["body"] = {
                        "start_line": body.start_point[0] + 1,
                        "end_line": body.end_point[0] + 1,
                        "preview": get_preview(body)
                    }
            # --- Ternary ---
            if n.type == "ternary_expression":
                cond = n.child_by_field_name("condition")
                flow["condition"] = get_preview(cond) if cond else None
                consequent = n.child_by_field_name("consequence")
                if consequent:
                    flow["consequent"] = {
                        "start_line": consequent.start_point[0] + 1,
                        "end_line": consequent.end_point[0] + 1,
                        "preview": get_preview(consequent)
                    }
                alternate = n.child_by_field_name("alternative")
                if alternate:
                    flow["alternate"] = {
                        "start_line": alternate.start_point[0] + 1,
                        "end_line": alternate.end_point[0] + 1,
                        "preview": get_preview(alternate)
                    }
            control_flows.append(flow)
        for child in n.children:
            walk(child)
    walk(node)
    return control_flows
    """
    Recursively extract control flow constructs from the AST node.
    Returns a list of dicts describing each control flow block,
    including consequent and alternate for if/ternary, and cases for switch.
    """
    control_flows = []

    def walk(n):
        if n.type in ("if_statement", "switch_statement", "ternary_expression",
                      "for_statement", "while_statement", "do_statement",
                      "for_in_statement", "for_of_statement"):
            flow = {
                "type": n.type,
                "start_line": n.start_point[0] + 1,
                "end_line": n.end_point[0] + 1,
                "source": code[n.start_byte:n.end_byte].decode()
            }
            # --- If statement ---
            if n.type == "if_statement":
                cond = n.child_by_field_name("condition")
                flow["condition"] = code[cond.start_byte:cond.end_byte].decode() if cond else None
                consequent = n.child_by_field_name("consequence")
                if consequent:
                    flow["consequent"] = code[consequent.start_byte:consequent.end_byte].decode()
                alternate = n.child_by_field_name("alternative")
                if alternate:
                    flow["alternate"] = code[alternate.start_byte:alternate.end_byte].decode()
            # --- Switch statement ---
            if n.type == "switch_statement":
                cond = n.child_by_field_name("value")
                flow["condition"] = code[cond.start_byte:cond.end_byte].decode() if cond else None
                # Collect all cases
                cases = []
                for child in n.children:
                    if child.type == "switch_case":
                        case_val = child.child_by_field_name("value")
                        case_body = child.child_by_field_name("body")
                        cases.append({
                            "case": code[case_val.start_byte:case_val.end_byte].decode() if case_val else "default",
                            "body": code[case_body.start_byte:case_body.end_byte].decode() if case_body else ""
                        })
                flow["cases"] = cases
            # --- Loops ---
            if n.type in ("for_statement", "while_statement", "do_statement", "for_in_statement", "for_of_statement"):
                cond = n.child_by_field_name("condition")
                flow["condition"] = code[cond.start_byte:cond.end_byte].decode() if cond else None
                body = n.child_by_field_name("body")
                if body:
                    flow["body"] = code[body.start_byte:body.end_byte].decode()
            # --- Ternary ---
            if n.type == "ternary_expression":
                cond = n.child_by_field_name("condition")
                flow["condition"] = code[cond.start_byte:cond.end_byte].decode() if cond else None
                consequent = n.child_by_field_name("consequence")
                if consequent:
                    flow["consequent"] = code[consequent.start_byte:consequent.end_byte].decode()
                alternate = n.child_by_field_name("alternative")
                if alternate:
                    flow["alternate"] = code[alternate.start_byte:alternate.end_byte].decode()
            control_flows.append(flow)
        for child in n.children:
            walk(child)
    walk(node)
    return control_flows
    """
    Recursively extract control flow constructs from the AST node.
    Returns a list of dicts describing each control flow block.
    """
    control_flows = []

    def walk(n):
        if n.type in ("if_statement", "switch_statement", "ternary_expression",
                      "for_statement", "while_statement", "do_statement",
                      "for_in_statement", "for_of_statement"):
            flow = {
                "type": n.type,
                "start_line": n.start_point[0] + 1,
                "end_line": n.end_point[0] + 1,
                "source": code[n.start_byte:n.end_byte].decode()
            }
            # Optionally, extract condition and body for if/switch/loops
            if n.type == "if_statement":
                cond = n.child_by_field_name("condition")
                flow["condition"] = code[cond.start_byte:cond.end_byte].decode() if cond else None
            if n.type == "switch_statement":
                cond = n.child_by_field_name("value")
                flow["condition"] = code[cond.start_byte:cond.end_byte].decode() if cond else None
            if n.type in ("for_statement", "while_statement", "do_statement", "for_in_statement", "for_of_statement"):
                cond = n.child_by_field_name("condition")
                flow["condition"] = code[cond.start_byte:cond.end_byte].decode() if cond else None
            if n.type == "ternary_expression":
                cond = n.child_by_field_name("condition")
                flow["condition"] = code[cond.start_byte:cond.end_byte].decode() if cond else None
            control_flows.append(flow)
        for child in n.children:
            walk(child)
    walk(node)
    return control_flows