import sys
from playwright.sync_api import sync_playwright

INDEX = r"C:\Users\Administrator\Desktop\Mirror\toolhelper-json\index.html"
URL = "file:///" + INDEX.replace("\\", "/")

sample = '{"b":2,"a":1,"dup":1,"dup":2,"nested":{"x":[1,2,3],"y":null},"note":"镜像 测试"}'

def run_once():
    blocked, file404, reqfailed, console_err, page_err = [], [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # 拦截一切非 file:// 请求（模拟断网）
        def route(r):
            u = r.request.url
            if u.startswith("file://"):
                r.continue_()
            else:
                blocked.append(u)
                r.abort()
        page.route("**/*", route)
        page.on("console", lambda m: console_err.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_err.append(str(e)))
        page.on("requestfailed", lambda r: reqfailed.append(f"{r.url} :: {str(r.failure or '?')}"))
        page.on("response", lambda r: file404.append(f"{r.status} {r.url}") if (r.url.startswith('file://') and r.status >= 400) else None)

        page.goto(URL, wait_until="networkidle", timeout=30000)
        try:
            page.wait_for_selector(".CodeMirror", state="attached", timeout=10000)
        except Exception as e:
            page_err.append(f"NO_Editor: {e}")
        # 设置输入
        page.evaluate("""(function(){
          var s = %s;
          var el = document.querySelector('.CodeMirror');
          if(el && el.CodeMirror) el.CodeMirror.setValue(s);
        })();""" % repr(sample))
        page.wait_for_timeout(400)
        # 真实点击各功能按钮
        for label in ("格式化", "校验", "压缩", "修复"):
            try:
                page.locator(f'button:has-text("{label}")').first.click(timeout=5000)
            except Exception as e:
                page_err.append(f"click {label} FAIL: {e}")
            page.wait_for_timeout(600)
        out = page.evaluate("""(function(){
          var el=document.querySelector('.CodeMirror');
          return el&&el.CodeMirror?el.CodeMirror.getValue():'';
        })();""")
        browser.close()
    return blocked, file404, reqfailed, console_err, page_err, out

for i in range(1, 4):
    blocked, file404, reqfailed, console_err, page_err, out = run_once()
    print(f"=== ROUND {i} ===")
    print("被拦截的外部请求:", len(blocked))
    for b in blocked:
        print("  BLOCK", b)
    print("file:// >=400 响应:", len(file404))
    for f in file404:
        print("  F404", f)
    print("requestfailed:", len(reqfailed))
    for r in reqfailed:
        print("  RF", r)
    print("console.error:", len(console_err))
    for c in console_err:
        print("  CE", c)
    print("pageerror:", len(page_err))
    for e in page_err:
        print("  PE", e)
    print("格式化后输出(head 200):", (out or "")[:200].replace("\n", "\\n"))
    print("输出含缩进(真格式化):", ("\n" in (out or "")) and ("  " in (out or "")))
    print()
