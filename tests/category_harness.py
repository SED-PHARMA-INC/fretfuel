"""Render the real theme with explicit Shopify adapters and synthetic products.

This is a local fixture, not a Shopify backend emulator. Shopify's schema and
paginate tags are removed; page slicing and pagination URLs are supplied here.
The real product-card, atlas-image, and pagination snippets are still rendered.
"""

import argparse
import copy
import html
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

from liquid import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TYPES = ("Guitar tuners", "Bass tuners", "Tremolo bridges", "Tailpieces",
         "Pickups", "Electronics", "Pickguards", "Saddles", "Knobs")
ROUTES = {"root_url": "/", "search_url": "/search",
          "all_products_collection_url": "/collections/all"}


def source(path, revision=None):
    if revision:
        return subprocess.check_output(
            ["git", "show", f"{revision}:{path}"], cwd=ROOT).decode("utf-8")
    return (ROOT / path).read_text(encoding="utf-8")


def prepare(text):
    text = re.sub(r"{%\s*schema\s*%}.*?{%\s*endschema\s*%}", "", text, flags=re.S)
    return re.sub(r"{%\s*(?:paginate\s+.*?|endpaginate)\s*%}", "", text)


def product(kind, number):
    return {"object_type": "product", "type": kind,
            "title": f"{kind or 'Uncategorized'} {number}",
            "url": f"/products/fixture-{number}", "price": 1000,
            "available": True, "featured_image": "", "price_varies": False,
            "selected_or_first_available_variant": {"sku": f"FIX-{number}"},
            "metafields": {"custom": {key: {"value": ""} for key in
                          ("series", "finish", "key_dimension")}}}


def catalog():
    rows = [product(kind, i) for i, kind in enumerate(TYPES)]
    rows += [product(TYPES[0], i) for i in range(9, 33)]
    rows += [product("", 33), product("Other parts", 34)]
    return rows


def quoted_type(query):
    """Independent query grammar: exactly one quoted field, with no operators."""
    match = re.fullmatch(r'product_type:"((?:[^"\\]|\\["\\])*)"', query)
    if match is None:
        return None
    return re.sub(r'\\(["\\])', r'\1', match[1])


class Theme:
    def __init__(self, revision=None):
        self.env = Environment(loader=FileSystemLoader(ROOT / "snippets", ext=".liquid"))
        self.env.add_filter("asset_url", lambda name: "/assets/" + name)
        self.env.add_filter("money", lambda value: f"${value / 100:.2f}")
        self.env.add_filter("within", lambda value, collection:
                            (collection.get("url", "") if isinstance(collection, dict) else "") + value)
        self.env.add_filter("image_url", lambda value, **kwargs: str(value))
        self.env.add_filter("image_tag", lambda value, **kwargs: '<img src="' + html.escape(str(value), quote=True) + '">')
        self.home = self.env.from_string(prepare(source("sections/ff-home.liquid", revision)))
        self.search = self.env.from_string(prepare(source("sections/ff-main-search.liquid", revision)))
        self.collection = self.env.from_string(prepare(source("sections/ff-main-collection.liquid", revision)))
        index = source("templates/index.json")
        self.index = json.loads(index[index.index("{"):])["sections"]["home"]
        schema = re.search(r"{% schema %}(.*?){% endschema %}", source("sections/ff-home.liquid"), re.S)[1]
        self.schema = json.loads(schema)

    def blocks(self):
        return [copy.deepcopy(self.index["blocks"][key]) for key in self.index["block_order"]]

    def render_home(self, blocks=None, routes=None):
        settings = {item["id"]: item.get("default", "") for item in self.schema["settings"]}
        settings.update(self.index["settings"])
        for name in ("featured_collection", "components_collection"):
            settings[name] = {"url": "/collections/all", "products": catalog()}
        blocks = copy.deepcopy(self.blocks() if blocks is None else blocks)
        for block in blocks:
            block["settings"].setdefault("image", "")
        return self.home.render(section={"settings": settings, "blocks": blocks},
                                routes=routes or ROUTES, collections={"all": settings["featured_collection"]})

    def render_search(self, query, rows=None, page=1, performed=True):
        rows = [] if rows is None else rows
        pages = max(1, math.ceil(len(rows) / 24))
        url = lambda number: "/search?" + urlencode({"type": "product", "q": query, "page": number})
        paginate = {"pages": pages, "current_page": page,
                    "previous": {"url": url(page - 1)} if page > 1 else None,
                    "next": {"url": url(page + 1)} if page < pages else None,
                    "parts": [{"title": n, "url": url(n), "is_link": n != page}
                              for n in range(1, pages + 1)]}
        return self.search.render(routes=ROUTES, paginate=paginate,
                                  search={"terms": query, "performed": performed,
                                          "results": rows[(page - 1) * 24:page * 24],
                                          "results_count": len(rows)})

    def page(self, path):
        parsed = urlsplit(path)
        params = parse_qs(parsed.query)
        if parsed.path == "/":
            body = self.render_home()
        elif parsed.path == "/search":
            query = params.get("q", [""])[0]
            kind = quoted_type(query)
            rows = [row for row in catalog() if row["type"] == kind] if kind is not None else [
                row for row in catalog() if query.lower() in row["title"].lower()]
            body = self.render_search(query, rows, page=int(params.get("page", [1])[0]), performed=bool(query))
        elif parsed.path == "/collections/all":
            body = self.collection.render(routes=ROUTES, paginate={"pages": 1},
                                          collection={"title": "All parts", "description": "",
                                                      "url": "/collections/all", "products": catalog()[:24],
                                                      "products_count": len(catalog()), "filters": [],
                                                      "sort_options": []})
        elif parsed.path.startswith("/products/fixture-"):
            row = next(row for row in catalog() if row["url"] == parsed.path)
            body = "<h1>" + html.escape(row["title"]) + "</h1>"
        else:
            raise FileNotFoundError(path)
        return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Local category test</title>'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<link rel="stylesheet" href="/assets/fretfuel.css">'
                '<link rel="stylesheet" href="/assets/fretfuel-theme.css">'
                '<script src="/assets/fretfuel-theme.js" defer></script><main>' + body + '</main></html>')


def handler(theme):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            try:
                path = urlsplit(self.path).path
                if path.startswith("/assets/"):
                    asset = (ROOT / path[1:]).resolve()
                    if not asset.is_relative_to(ROOT / "assets"):
                        raise FileNotFoundError(path)
                    if asset.name == "fretfuel.css":
                        payload = theme.env.from_string(source("assets/fretfuel.css.liquid")).render().encode()
                    else:
                        payload = asset.read_bytes()
                    kind = "text/css" if path.endswith(".css") else "text/javascript" if path.endswith(".js") else "application/octet-stream"
                else:
                    payload = theme.page(self.path).encode("utf-8")
                    kind = "text/html; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (FileNotFoundError, ValueError, StopIteration):
                self.send_error(404)
    return Handler


def benchmark(base):
    themes = {"baseline": Theme(base), "updated": Theme()}
    results = {}
    for name, theme in themes.items():
        for _ in range(10):
            theme.render_home()
        timings = []
        for _ in range(200):
            start = time.perf_counter()
            output = theme.render_home()
            timings.append((time.perf_counter() - start) * 1000)
        results[name] = {"samples": len(timings), "median_ms": round(statistics.median(timings), 3),
                         "p95_ms": round(sorted(timings)[189], 3), "html_bytes": len(output.encode())}
    results["passes"] = (results["updated"]["p95_ms"] < 50 and
                         results["updated"]["p95_ms"] - results["baseline"]["p95_ms"] < 15)
    print(json.dumps(results, indent=2))
    return results["passes"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", type=int)
    parser.add_argument("--benchmark", metavar="BASE_REVISION")
    options = parser.parse_args()
    if options.serve:
        server = ThreadingHTTPServer(("127.0.0.1", options.serve), handler(Theme()))
        print(f"Synthetic fixture at http://127.0.0.1:{server.server_port}/", flush=True)
        server.serve_forever()
    elif options.benchmark:
        raise SystemExit(0 if benchmark(options.benchmark) else 1)
