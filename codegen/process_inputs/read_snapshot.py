# read_snapshot.py

from pathlib import Path

from parsers.dom_parser import parse_dom

def read_snapshot_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    return html

if __name__ == "__main__":
    snapshot_path = "testdata/snapshot.html"  # or full path like './data/snapshot.html'
    html_content = read_snapshot_file(snapshot_path)

    # Parse the DOM
    metadata_tree = parse_dom([html_content])

    # Optional: pretty print the result
    import json
    import os
    output_dir = "testdata/output"
    print(f"Extracted {len(metadata_tree)}")
    for req in metadata_tree[:5]:  # Show first 5 for brevity
        print(json.dumps(req, indent=2))

    with open(os.path.join(output_dir, f"element_metadata.json"), "w") as pf:
            json.dump(metadata_tree, pf, indent=2)
    
