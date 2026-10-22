"""旧サイト (https://w-mtlab.info/) をスクレイピングして Hugo のコンテンツに変換する移行用スクリプト.

使い方:
    .venv/bin/python tools/scrape.py

content/{ja,en}/ 以下の Markdown と static/img/ 以下の画像を (上書きで) 生成する.
"""

import re
import sys
import warnings
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Comment, NavigableString, Tag, XMLParsedAsHTMLWarning
from markdownify import MarkdownConverter

# 旧サイトは XHTML (XML宣言付き) だが HTML として解釈する
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BASE_URL = "https://w-mtlab.info/"
ROOT = Path(__file__).resolve().parent.parent

# 旧ページ -> (言語, 新しいコンテンツパス, タイトル, 新URL)
PAGES = {
    "index.php": ("ja", "_index.md", "トップページ", "/"),
    "members.php": ("ja", "members.md", "構成員・設備", "/members/"),
    "research.php": ("ja", "research.md", "研究テーマ", "/research/"),
    "publications.php": ("ja", "publications.md", "研究業績", "/publications/"),
    "welcome.php": ("ja", "join.md", "配属希望の皆様へ", "/join/"),
    "links.php": ("ja", "links.md", "リンク", "/links/"),
    "ask.php": ("ja", "contact.md", "お問い合わせ", "/contact/"),
    "index-e.php": ("en", "_index.md", "Top page", "/en/"),
    "research-e.php": ("en", "research.md", "Research Theme", "/en/research/"),
    "publications-e.php": ("en", "publications.md", "Publication", "/en/publications/"),
    "ask-e.php": ("en", "contact.md", "Contact Information", "/en/contact/"),
}

# 旧URL -> 新URL (サイト内リンクの書き換え用)
LINK_MAP = {old: new for old, (_, _, _, new) in PAGES.items()}
LINK_MAP["index.html"] = "/"


class Converter(MarkdownConverter):
    """表・定義リスト・図はHTMLのまま / Hugoショートコードとして出力する."""

    def convert_table(self, el, text, convert_as_inline):
        return "\n\n" + raw_html(el) + "\n\n"

    def convert_dl(self, el, text, convert_as_inline):
        return "\n\n" + raw_html(el) + "\n\n"

    def convert_img(self, el, text, convert_as_inline):
        return figure(el.get("src"), el.get("alt", ""))

    def convert_figure(self, el, text, convert_as_inline):
        img = el.find("img")
        cap = el.find("figcaption")
        return figure(img.get("src"), img.get("alt", ""), cap.get_text(strip=True) if cap else "")


def figure(src, alt, caption=""):
    attrs = f'src="{src}" alt="{alt}"'
    if caption:
        attrs += f' caption="{caption}"'
    return "\n\n{{< figure " + attrs + " >}}\n\n"


def raw_html(el):
    """表などをHTMLのまま埋め込む. 中身のインデントを揃えて Markdown のコードブロック扱いを防ぐ."""
    # 図はサブパス公開でも画像パスが解決されるようショートコードにする
    for fig in el.find_all("figure"):
        img = fig.find("img")
        cap = fig.find("figcaption")
        fig.replace_with(figure(img.get("src"), img.get("alt", ""), cap.get_text(strip=True) if cap else "").strip())
    html = el.decode(formatter="minimal")
    html = html.replace("{{&lt;", "{{<").replace("&gt;}}", ">}}")
    html = html.replace("</tr>", "</tr>\n")
    lines = [ln.strip() for ln in html.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def rewrite_url(url, attr, lang="ja"):
    if not url or url.startswith(("http://", "https://", "mailto:", "#")):
        return url
    if attr == "src":
        return "/" + url.removeprefix("./").lstrip("/")
    new = LINK_MAP.get(url, url)
    # Hugo のリンク解決は言語ごとなので, 英語ページ内のリンクは /en を付けない
    if lang == "en":
        new = new.removeprefix("/en")
    return new


def clean(soup, contents, lang):
    # コメントアウトされた古い情報は移行しない
    for c in contents.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()

    for a in contents.find_all("a", href=True):
        a["href"] = rewrite_url(a["href"], "href", lang)
    for img in contents.find_all("img", src=True):
        img["src"] = rewrite_url(img["src"], "src")

    # <img> + <p class="caption"> を <figure> にまとめる
    for cap in contents.find_all("p", class_="caption"):
        img = cap.find_previous_sibling()
        if isinstance(img, Tag) and img.name == "img":
            fig = soup.new_tag("figure")
            img.wrap(fig)
            fc = soup.new_tag("figcaption")
            fc.string = cap.get_text(strip=True)
            fig.append(fc)
            cap.decompose()

    # <ul> 直下の <li> 外テキスト (受賞注記・引用文) を直前の <li> に取り込む
    for ul in contents.find_all(["ul", "ol"]):
        last_li = None
        for node in list(ul.children):
            if isinstance(node, Tag) and node.name == "li":
                last_li = node
                continue
            if isinstance(node, NavigableString) and not node.strip():
                continue
            if isinstance(node, Tag) and node.name == "br":
                node.extract()
                continue
            if last_li is None:
                continue
            text = node.strip() if isinstance(node, NavigableString) else None
            node.extract()
            last_li.append(soup.new_tag("br"))
            if text is not None:
                last_li.append(text.strip("　 "))
            else:
                last_li.append(node)

    # 段落末尾の <br> (直後が </p>) は不要
    for p in contents.find_all("p"):
        while p.contents and (
            (isinstance(p.contents[-1], Tag) and p.contents[-1].name == "br")
            or (isinstance(p.contents[-1], NavigableString) and not p.contents[-1].strip())
        ):
            p.contents[-1].extract()

    # 区切り用の単独 <br />
    for br in contents.find_all("br"):
        if br.parent is contents:
            br.decompose()


def to_markdown(contents):
    md = Converter(heading_style="ATX", bullets="-", newline_style="backslash", escape_underscores=False, escape_asterisks=False).convert_soup(contents)
    md = md.replace(" ", " ")
    md = re.sub(r"[ \t]+\n", "\n", md)
    # <br> の前後に残った空行・空白だけの行を詰める
    md = re.sub(r"\n[ \t]*\\\n", " \\\n", md)
    md = re.sub(r"\\\n(?:[ \t]*\n)+", "\\\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    # 段落内の改行 (<br>) は Markdown の行末バックスラッシュで表現される
    return md.strip() + "\n"


def front_matter(title, weight, aliases):
    lines = ["+++", f"title = '{title}'"]
    if weight is not None:
        lines.append(f"weight = {weight}")
    if aliases:
        lines.append("aliases = [" + ", ".join(f"'{a}'" for a in aliases) + "]")
    lines.append("+++")
    return "\n".join(lines) + "\n\n"


def main():
    session = requests.Session()
    images = set()

    for weight, (old, (lang, path, title, _new)) in enumerate(PAGES.items()):
        resp = session.get(urljoin(BASE_URL, old), timeout=30)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
        contents = soup.find("div", id="contents")

        images.update(rewrite_url(img["src"], "src") for img in contents.find_all("img", src=True))
        clean(soup, contents, lang)
        md = to_markdown(contents)

        # 旧URL (/xxx.php) からのリダイレクト. GitHub Pages では xxx.php/ ディレクトリとして生成する.
        # 英語ページの alias は /en/ 基準になるため ../ でサイトルートに戻す
        aliases = [f"/{old}/" if lang == "ja" else f"../{old}/"]
        out = ROOT / "content" / lang / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(front_matter(title, None if path == "_index.md" else weight, aliases) + md, encoding="utf-8")
        print(f"{old:22} -> content/{lang}/{path}")

    for src in sorted(images):
        dest = ROOT / "static" / src.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        resp = session.get(urljoin(BASE_URL, src), timeout=30)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        print(f"{src:22} -> static/{src.lstrip('/')}")


if __name__ == "__main__":
    sys.exit(main())
