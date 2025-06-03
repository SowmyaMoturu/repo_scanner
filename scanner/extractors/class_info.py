
import re
from scanner.ast_utils import get_node_text, find_class_declarations

def resolve_locator_arg(arg, locators_map):
    if isinstance(arg, str) and arg.startswith("locators.") or arg.startswith("locators["):
        key = arg.split(".", 1)[1]
        resolved = locators_map.get(key)
        if isinstance(resolved, dict):
            return resolved.get("value", arg)
        return resolved or arg
    return arg

def extract_locators_map(code):
    """
    Captures: locators defined as locators = { ... }
    """
    locators_map = {}
    text = code.decode()
    pattern = re.compile(r"locators\s*=\s*{([^}]+)}", re.DOTALL)
    matches = pattern.finditer(text)
    for match in matches:
        body = match.group(1)
        for line in body.splitlines():
            kv = line.strip().split(":")
            if len(kv) == 2:
                key = kv[0].strip().strip('",\'')
                value = kv[1].strip().strip('",\'')
                locators_map[key] = value
    return locators_map


def extract_class_inheritance(tree, code):
    """
    Robustly captures class inheritance (class_parents) for TS/JS.
    Handles: class Foo extends Bar { ... }
    """
    root = tree.root_node
    class_parents = {}
    class_nodes = find_class_declarations(root)
    for node in class_nodes:
        name_node = node.child_by_field_name("name")
        class_name = get_node_text(code, name_node) if name_node else None
        parent_class = None
       
        print(f"[INHERITANCE] Processing class: {class_name}")

        parent_class = None

        for child in node.children:
            if child.type == "class_heritage":
                for grandchild in child.children:
                    if grandchild.type == "extends_clause":
                        # ✅ Directly pull the 'value' field under extends_clause
                        value_node = grandchild.child_by_field_name("value")
                        if value_node and value_node.type in ("identifier", "qualified_name"):
                            parent_class = get_node_text(code, value_node)
                            break


        if class_name:
            class_parents[class_name] = parent_class
            print(f"[INHERITANCE] Class: {class_name}, Parent: {parent_class}")
    return class_parents
