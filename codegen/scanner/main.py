from build_map.build_feature_map import build_feature_map
from scanners.page_scanner import scan_multiple_directories
from scanners.step_scanner import scan_step_definitions
from build_map.method_index import build_index
from build_map.link_step_calls import get_links

if __name__ == "__main__":
    page_dirs = [
        "src/pages",
        "src/utils",
        "src/api.calls",
        "src/setup"
    ]
    scan_multiple_directories(page_dirs)
    scan_step_definitions("src/step-definitions")
    build_index()
    get_links()
    build_feature_map("src/features", "scanner/scan_split")
