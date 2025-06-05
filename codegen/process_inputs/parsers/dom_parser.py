import json
from bs4 import BeautifulSoup, Tag

EXCLUDED_TAGS = {"script", "noscript", "style", "meta", "link"}

def extract_aria_attrs(el):
    return {k: v for k, v in el.attrs.items() if k.startswith("aria-")}

def element_to_flat(el, path=None, parent_testid=None, flat=None):
    """
    Recursively flattens the DOM tree rooted at `el` into a flat list of elements,
    each with a unique index-aware path and relevant metadata.
    """
    if flat is None:
        flat = []
    if not el or not hasattr(el, "name"):
        return flat
    if el.name in EXCLUDED_TAGS:
        return flat

    testid = el.get("data-testid")
    text = el.get_text(strip=True)
    max_text_len = 50

    # Count previous siblings of the same tag to get the index
    index = 0
    if el.parent and hasattr(el.parent, "children"):
        for sibling in el.parent.children:
            if not isinstance(sibling, Tag):
                continue
            if sibling is el:
                break
            if sibling.name == el.name:
                index += 1
    tag_with_index = f"{el.name}[{index}]"
    current_path = f"{path}.{tag_with_index}" if path else tag_with_index

    raw_metadata = {
        "tag": el.name,
        "text": text[:max_text_len] if text else None,
        "data-testid": testid,
        "id": el.get("id"),
        "name": el.get("name"),
        "class": el.get("class"),
        "type": el.get("type"),
        "placeholder": el.get("placeholder"),
        "role": el.get("role"),
        "aria": extract_aria_attrs(el),
        "path": current_path,
        "parentTestId": parent_testid
    }
    metadata = {k: v for k, v in raw_metadata.items() if v not in (None, {}, [], "")}
    if len(metadata) > 2:
        flat.append(metadata)

    for child in el.children:
        if isinstance(child, Tag):
            element_to_flat(child, path=current_path, parent_testid=testid or parent_testid, flat=flat)
    return flat

def parse_dom(dom_contents):
    """
    Parses a list of HTML DOM strings and returns a flat list of elements with index-aware paths.
    """
    elements = []
    for dom in dom_contents:
        soup = BeautifulSoup(dom, 'html.parser')
        root = soup.body or soup.html or soup
        elements.extend(element_to_flat(root))
    # 1. Filter actionable/relevant elements
    filtered = [el for el in elements if is_actionable(el)]

# 2. Remove duplicates
    filtered = dedupe(filtered)

# 3. Keep only first N from each group (table/list)
    filtered = keep_first_n_from_groups(filtered, n=2)
    return filtered



def is_actionable(el):
    actionable_tags = {"button", "input", "select", "textarea", "form", "a"}
    if el.get("tag") in actionable_tags:
        return True
    if el.get("tag") == "a" and el.get("href"):
        return True
    if el.get("id") or el.get("data-testid"):
        return True
    if el.get("text") and len(el["text"].strip()) > 2:
        return True
    return False

def dedupe(elements):
    seen = set()
    unique = []
    for el in elements:
        key = (el.get("tag"), tuple(el.get("class", [])), el.get("text", ""))
        if key not in seen:
            seen.add(key)
            unique.append(el)
    return unique

def keep_first_n_from_groups(elements, n=2):
    # Only keep first n elements from each parent path group (e.g., table/list)
    groups = {}
    for el in elements:
        parent = ".".join(el["path"].split(".")[:-1])
        groups.setdefault(parent, []).append(el)
    result = []
    for group in groups.values():
        result.extend(group[:n])
    return result

