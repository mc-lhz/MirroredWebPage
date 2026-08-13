import os, re

OUT = r"C:\Users\Administrator\Desktop\Mirror\toolhelper-json"
TEXT_EXTS = {".html", ".htm", ".css", ".js", ".json", ".svg", ".xml", ".webmanifest", ".txt"}

# 1) 入口文档 JSON/JSONFormat -> index.html（覆盖式）
src = os.path.join(OUT, "JSON", "JSONFormat")
dst = os.path.join(OUT, "index.html")
if os.path.exists(src):
    if os.path.exists(dst):
        os.remove(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.rename(src, dst)
    print("renamed JSON/JSONFormat -> index.html")
jsondir = os.path.join(OUT, "JSON")
if os.path.isdir(jsondir):
    try:
        os.rmdir(jsondir)
    except OSError:
        pass

# 2) 收集所有本地资源绝对路径 key
keys = []
for root, dirs, files in os.walk(OUT):
    for fn in files:
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, OUT).replace(os.sep, "/")
        keys.append("/" + rel)
keys = sorted(set(keys), key=len, reverse=True)

def depth_of(relpath):
    d = os.path.dirname(relpath)
    return 0 if d == "" else len(d.split("/"))

# 3) 逐文本文件：把绝对本地引用 /X 改写为按文件深度的相对路径
rewritten = 0
for root, dirs, files in os.walk(OUT):
    for fn in files:
        ext = os.path.splitext(fn)[1].lower()
        if ext not in TEXT_EXTS:
            continue
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, OUT).replace(os.sep, "/")
        depth = depth_of(rel)
        try:
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            continue
        orig = content
        for k in keys:
            if k == "/" + rel:
                continue
            relpath = ("../" * depth) + k[1:]
            for form in (k, "https://www.toolhelper.cn" + k,
                         "http://www.toolhelper.cn" + k,
                         "//www.toolhelper.cn" + k):
                content = re.sub(re.escape(form) + r"(\?[^\"')\s]*)?",
                                 relpath, content)
        if content != orig:
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            rewritten += 1
            print(f"rewrote {rel} (depth {depth})")
print("rewritten files:", rewritten)

# 4) 剥离 Google 广告（仅外部资源加载，导航链接 beian 等保留）
idx = os.path.join(OUT, "index.html")
with open(idx, "r", encoding="utf-8") as f:
    html = f.read()
html = re.sub(r'<script[^>]*src="[^"]*(googlesyndication|doubleclick|adtraffic|pagead|googleads|wwads)[^"]*"[^>]*>\s*</script>',
              "", html, flags=re.I)
def _filter(m):
    return "" if ("adsbygoogle" in m.group(0) or "wwads" in m.group(0)) else m.group(0)
html = re.sub(r"<script[^>]*>.*?</script>", _filter, html, flags=re.I | re.S)
html = re.sub(r'<ins\b[^>]*class="[^"]*adsbygoogle[^"]*"[^>]*>.*?</ins>', "", html, flags=re.I | re.S)
html = re.sub(r'<div\b[^>]*class="[^"]*wwads[^"]*"[^>]*>.*?</div>', "", html, flags=re.I | re.S)
html = re.sub(r'<link[^>]*href="[^"]*(googleapis|gstatic)[^"]*"[^>]*>', "", html, flags=re.I)
with open(idx, "w", encoding="utf-8") as f:
    f.write(html)
print("removed ad/tracking refs from index.html")

# 5) 残留外部域名自检
print("=== 入口HTML残留外部域名(应只剩导航类) ===")
for m in re.findall(r'https?://[^\s"\'<>)+]+', html):
    if "toolhelper.cn" not in m and "w3.org/2000/svg" not in m:
        print("  EXT:", m)
