import os
import json

from parsers.har_parser import parse_har

HAR_PATH = "testdata/opensource-demo.orangehrmlive.com.har"

def main():
    if not os.path.exists(HAR_PATH):
        print(f"File not found: {HAR_PATH}")
        return

    with open(HAR_PATH, "r", encoding="utf-8") as f:
        har_raw = f.read()

    xhr_requests = parse_har(har_raw)

    print(f"Extracted {len(xhr_requests)} XHR/fetch requests.")
    for req in xhr_requests[:5]:  # Show first 5 for brevity
        print(json.dumps(req, indent=2))

    # Optionally, save to a file
    with open("testdata/output/xhr_requests.json", "w", encoding="utf-8") as out:
        json.dump(xhr_requests, out, indent=2)

if __name__ == "__main__":
    main()