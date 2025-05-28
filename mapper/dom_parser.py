from bs4 import BeautifulSoup

def parse_dom(dom_contents):
    extracted_data = []
    for dom in dom_contents:
        soup = BeautifulSoup(dom, 'html.parser')
        elements = soup.find_all(["h1", "h2", "p", "button", "input", "span", "div"])
        for el in elements:
            text = el.get_text(strip=True)
            if text:
                extracted_data.append({"text": text, "html": str(el)})
    return extracted_data