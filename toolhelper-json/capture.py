import os, sys, json
from urllib.parse import urlparse, urlunparse
from playwright.sync_api import sync_playwright

BASE_HOST = "www.toolhelper.cn"
OUT = r"C:\Users\Administrator\Desktop\Mirror\toolhelper-json"
URL = "https://www.toolhelper.cn/JSON/JSONFormat"

os.makedirs(OUT, exist_ok=True)

saved = {}        # local absolute path (no query) -> local file
external = []     # external requests (host != toolhelper.cn)
failed = []       # requests that failed (status>=400 or error)

def local_path_for(u):
    p = urlparse(u)
    if p.netloc.lower() not in (BASE_HOST, "toolhelper.cn"):
        return None
    path = p.path or "/"
    if path.endswith("/"):
        path += "index.html"
    if path == "/":
        path = "/index.html"
    return path  # absolute-from-root, starts with /

def write_file(relpath, data):
    full = os.path.join(OUT, relpath.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    mode = "wb"
    if isinstance(data, str):
        data = data.encode("utf-8")
    with open(full, mode) as f:
        f.write(data)

sample = '''{"name":"toolhelper","list":[1,2,3],"nested":{"a":1,"b":[true,false,null],"messy":   {"x":1,"y":2}},"dup":1,"dup":2,"note":"测试 镜像"}'''

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("response", lambda r: save_response(r))
    page.on("requestfailed", lambda r: failed.append(f"FAIL {r.url} :: {str(r.failure or '?')}"))

    def save_response(r):
        u = r.url
        lp = local_path_for(u)
        if lp is None:
            external.append(f"{r.request.resource_type} {u}")
            return
        try:
            body = r.body()
        except Exception as e:
            failed.append(f"NOBODY {r.status} {u} :: {e}")
            return
        if r.status >= 400:
            failed.append(f"HTTP{r.status} {u}")
        write_file(lp, body)
        saved[lp] = len(body)

    page.goto(URL, wait_until="networkidle", timeout=60000)
    # wait for codemirror
    try:
        page.wait_for_selector(".CodeMirror", timeout=15000)
    except Exception as e:
        print("WARN: .CodeMirror not found:", e)
    # interact: set value + exercise functions
    try:
        page.evaluate("""(function(){
          var s = %s;
          var el = document.querySelector('.CodeMirror');
          if(el && el.CodeMirror){ el.CodeMirror.setValue(s); }
          else { var t=document.getElementById('txtInput'); if(t){ t.value=s; } }
        })();""" % json.dumps(sample))
        page.wait_for_timeout(500)
        page.evaluate("if(typeof jsonFormat==='function') jsonFormat();")
        page.wait_for_timeout(800)
        page.evaluate("if(typeof compress==='function') compress();")
        page.wait_for_timeout(500)
        page.evaluate("if(typeof jsonRepair==='function') jsonRepair();")
        page.wait_for_timeout(500)
        page.evaluate("if(typeof codeMirrorFoldOrUnfoldAll==='function') codeMirrorFoldOrUnfoldAll(document.querySelector('.btn'));")
    except Exception as e:
        print("WARN interaction:", e)
    # read editor value after format (re-set + format to capture output)
    try:
        out = page.evaluate("""(function(){
          var el=document.querySelector('.CodeMirror');
          if(el&&el.CodeMirror) return el.CodeMirror.getValue();
          return '';
        })();""")
        print("EDITOR_VALUE_AFTER_LEN:", len(out or ""))
        print("EDITOR_VALUE_HEAD:", (out or "")[:120])
    except Exception as e:
        print("WARN read:", e)
    page.wait_for_timeout(1000)
    try:
        page.screenshot(path=os.path.join(OUT, "_capture.png"), full_page=False)
    except Exception as e:
        print("WARN shot:", e)
    browser.close()

print("=== SAVED FILES:", len(saved))
for k in sorted(saved):
    print(f"  {k}  ({saved[k]}B)")
print("=== EXTERNAL REQUESTS:", len(external))
for e in sorted(set(external)):
    print("  EXT", e)
print("=== FAILED/4xx:", len(failed))
for f in failed:
    print("  FAIL", f)
