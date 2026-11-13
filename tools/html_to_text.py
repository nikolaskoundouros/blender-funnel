"""Reduce a downloaded documentation page to its article text.

Usage: python -I html_to_text.py page.html [page2.html ...]
Writes page.txt next to each input. Navigation, scripts and sidebars are dropped.
"""
import pathlib
import re
import sys

from bs4 import BeautifulSoup


def main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "svg"]):
        tag.decompose()
    node = (
        soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.find("main")
        or soup.body
        or soup
    )
    text = node.get_text("\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


for arg in sys.argv[1:]:
    src = pathlib.Path(arg)
    out = src.with_suffix(".txt")
    out.write_text(main_text(src.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
    print(f"{out.name}: {len(out.read_text(encoding='utf-8').split())} words")
