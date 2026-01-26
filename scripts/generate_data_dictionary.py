import json
import re
from html.parser import HTMLParser
from pathlib import Path


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_td = False
        self.in_th = False
        self.current_row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag in ("td", "th"):
            if tag == "td":
                self.in_td = True
            else:
                self.in_th = True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.in_td = False
            self.in_th = False
        if tag == "tr":
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = []

    def handle_data(self, data):
        if self.in_td or self.in_th:
            text = data.strip()
            if text:
                self.current_row.append(text)


def extract_tables(markdown_text: str) -> list[dict]:
    tables = []
    for table_match in re.finditer(r"<table>.*?</table>", markdown_text, re.DOTALL):
        table_html = table_match.group(0)
        parser = TableParser()
        parser.feed(table_html)
        if parser.rows:
            headers = parser.rows[0]
            rows = parser.rows[1:] if len(parser.rows) > 1 else []
            tables.append({"headers": headers, "rows": rows})
    return tables


def extract_titles(markdown_text: str) -> list[str]:
    titles = []
    for line in markdown_text.splitlines():
        if line.strip().startswith("表 "):
            titles.append(line.strip())
    return titles


def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    md_path = base_dir / "MinerU_markdown_1标准正文-农业物联网 大田环境感知数据接入要求(2)_20260126164505_2015707552499785728.md"
    content = md_path.read_text(encoding="utf-8")
    tables = extract_tables(content)
    titles = extract_titles(content)
    combined = []
    for index, table in enumerate(tables):
        title = titles[index] if index < len(titles) else f"表 {index + 1}"
        combined.append({"title": title, "headers": table["headers"], "rows": table["rows"]})
    output = {
        "source": md_path.name,
        "tables": combined,
    }
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "data_dictionary.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
