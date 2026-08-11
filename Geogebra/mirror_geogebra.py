import os, urllib.request
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

TARGET = "https://www.geogebra.org/calculator"
OUT = r"C:\Users\Administrator\Desktop\Mirror\geogebra-mirror"
os.makedirs(OUT, exist_ok=True)
APPS = ["Graphing", "3D Calculator", "Geometry", "CAS", "Probability", "Scientific", "Spreadsheet"]
FRAG_PROBE_MAX = 40

# Use the SERVER HTML for the entry document. pg.content() returns the LIVE
# DOM after GWT has already booted and injected fragments; saving that bakes
# runtime artifacts (a duplicate <script src="...nocache.js">, an already-open
# app-picker, a pre-rendered #ggbApplet, etc.) into the file. On reload those
# artifacts cause the GWT module to boot multiple times and produce an
# unusable scroll-offset layout.
main_html_bytes = None

mapping = {}
CT_EXT = {
    "application/javascript": ".js", "text/javascript": ".js", "application/x-javascript": ".js",
    "text/css": ".css", "application/wasm": ".wasm", "application/json": ".json",
    "image/svg+xml": ".svg", "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
    "image/webp": ".webp", "font/woff": ".woff", "font/woff2": ".woff2",
    "application/font-woff": ".woff", "application/octet-stream": ".bin",
    "text/plain": ".txt", "application/x-gwt-rpc": ".txt",
}

def ext_for(ct):
    if ct:
        c = ct.split(";")[0].strip().lower()
        if c in CT_EXT:
            return CT_EXT[c]
    return ".bin"

def save_path(url, ct):
    p = urlparse(url)
    host = p.netloc
    path = p.path
    if path == "":
        path = "/index" + ext_for(ct)
    elif path.endswith("/"):
        path = path + "index" + ext_for(ct)
    elif "." not in path.rsplit("/", 1)[-1]:
        path = path + ext_for(ct)
    if not path.startswith("/"):
        path = "/" + path
    if host == "www.geogebra.org":
        rel = path
        fpath = OUT + path
    else:
        rel = "/" + host + path
        fpath = os.path.join(OUT, host + path)
    return rel, fpath

def should_capture(url):
    return not (url.startswith("data:") or url.startswith("blob:") or url.startswith("about:"))

def register(url, rel):
    if url not in mapping:
        mapping[url] = rel
        if url.startswith("https:"):
            mapping["//" + url[8:]] = rel
            mapping["http://" + url[8:]] = rel
        elif url.startswith("http:"):
            mapping["//" + url[7:]] = rel

def on_response(response):
    global main_html_bytes
    url = response.request.url
    if url == TARGET:
        try:
            if response.status == 200:
                main_html_bytes = response.body()
        except Exception:
            pass
        return
    if not should_capture(url):
        return
    try:
        if response.status != 200:
            return
        ct = response.headers.get("content-type", "")
        body = response.body()
    except Exception:
        return
    if not body:
        return
    rel, fpath = save_path(url, ct)
    register(url, rel)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(fpath, "wb") as f:
        f.write(body)

def rewrite(content):
    for url, rel in mapping.items():
        if len(url) > 8:
            content = content.replace(url, rel)
    return content

print("[1/4] loading page + exercising modes ...")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1366, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36")
    pg.on("response", on_response)
    pg.goto(TARGET, wait_until="load", timeout=90000)
    try: pg.wait_for_load_state("networkidle", timeout=40000)
    except Exception: pass
    pg.wait_for_timeout(10000)
    for app in APPS:
        pg.evaluate("""() => { const x=document.querySelector('.suiteAppPickerButton'); if(x) x.click(); }""")
        pg.wait_for_timeout(1500)
        pg.evaluate("""(txt) => {
          const rows=Array.from(document.querySelectorAll('.appPickerRow, .appPickerLabel'));
          for(const r of rows){ if((r.textContent||'').trim()===txt){ r.click(); return; } }
          const all=Array.from(document.querySelectorAll('*'));
          for(const e of all){ if((e.textContent||'').trim()===txt){ e.click(); return; } }
        }""", app)
        try: pg.wait_for_load_state("networkidle", timeout=20000)
        except Exception: pass
        pg.wait_for_timeout(6000)
    b.close()

if main_html_bytes:
    html = main_html_bytes.decode("utf-8", errors="replace")
    print("[info] using raw server HTML as entry document")
else:
    print("[warn] did not capture main document response; falling back to rendered DOM")
    html = pg.content()

# detect deferredjs base + hash
deferred_base = None
for u in mapping:
    if "/deferredjs/" in u:
        deferred_base = u[:u.rfind("/") + 1]
        break
print("[2/4] deferredjs base:", deferred_base)

print(f"[3/4] probing fragments 1..{FRAG_PROBE_MAX} to fill gaps ...")
if deferred_base:
    for n in range(1, FRAG_PROBE_MAX + 1):
        furl = deferred_base + f"{n}.cache.js"
        if furl in mapping:
            continue
        try:
            req = urllib.request.Request(furl, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=60).read()
            rel, fpath = save_path(furl, "text/javascript")
            register(furl, rel)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "wb") as f:
                f.write(data)
            print("   fetched", n, len(data))
        except Exception as e:
            pass  # 404 or not present

print("[4/4] rewriting index.html + text assets ...")
html2 = rewrite(html)
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
    f.write(html2)

text_exts = (".js", ".css", ".json", ".html", ".svg", ".xml", ".txt", ".ftl")
for url, rel in list(mapping.items()):
    p = urlparse(url)
    fpath = OUT + rel if p.netloc == "www.geogebra.org" else os.path.join(OUT, p.netloc + rel)
    if not os.path.exists(fpath) or not fpath.endswith(text_exts):
        continue
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            c = f.read()
    except Exception:
        continue
    c2 = rewrite(c)
    if c2 != c:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(c2)

print("mapping entries:", len(mapping))
print("index.html bytes:", os.path.getsize(os.path.join(OUT, "index.html")))
print("total files:", sum(len(fspath) for _, _, fspath in os.walk(OUT) if os.path.isfile(os.path.join(_, fspath))) if False else 0)
