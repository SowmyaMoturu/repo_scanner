from tree_sitter import Language, Parser
from tree_sitter_typescript import language_typescript

# Get the TypeScript language
TS_LANGUAGE = Language(language_typescript())

# Create a parser, passing the language directly to the constructor
parser =Parser(language=TS_LANGUAGE)

# Sample TypeScript code
ts_code = """
function greet(name: string): string {
    const message = `Hello, ${name}!`;
    return message;
}

interface User {
    id: number;
    name: string;
}

const user: User = { id: 1, name: "Alice" };
console.log(greet(user.name));
"""

# Parse the code
tree = parser.parse(ts_code.encode('utf-8'))

# Get the root node of the syntax tree
root_node = tree.root_node


tree = parser.parse(ts_code.encode('utf-8'))
root_node = tree.root_node



print("\n--- Root Node Details (Accessed directly on the Node object) ---")
# These properties are directly on the root_node object
print(f"Node type: {root_node.type}")
print(f"Start point: {root_node.start_point}")
print(f"End point: {root_node.end_point}")
print(f"Start byte: {root_node.start_byte}")
print(f"End byte: {root_node.end_byte}")
print(f"Text content: {root_node.text.decode('utf-8')[:50]}...") # Print first 50 chars for brevity

print("\n--- Example: Accessing details for a specific child node (e.g., 'greet' function) ---")
# Let's find the 'greet' function's identifier node and print its details
for child in root_node.children:
    if child.type == 'function_declaration':
        # Now iterate through the children of the function_declaration node
        for func_child in child.children:
            if func_child.type == 'identifier': # This is the 'greet' identifier node
                print(f"  Identifier Node Type: {func_child.type}")
                print(f"  Identifier Node Text: {func_child.text.decode('utf-8')}")
                print(f"  Identifier Node Start Point: {func_child.start_point}")
                print(f"  Identifier Node End Point: {func_child.end_point}")
                break # Found it, so break out of inner loop
        break # Found function declaration, so break out of outer loop
