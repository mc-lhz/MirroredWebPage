#!/usr/bin/env python
# Desmos 离线验证：file:// 双击打开 + 断网 + 真实输入计算。
from playwright.sync_api import sync_playwright

URL = "file:///C:/Users/Administrator/Desktop/Mirror/Desmos/index.html"
external, page_errors, console_errors = [], [], []


def route(r):
    if r.request.url.startswith("file://"):
        r.continue_()
    else:
        external.append(r.request.url)
        r.abort()


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.route("**", route)
    pg.on("pageerror", lambda e: page_errors.append(str(e)[:200]))
    pg.on(
        "console",
        lambda m: console_errors.append(m.text[:200]) if m.type == "error" else None,
    )

    pg.goto(URL)
    # 等待表达式编辑器渲染
    try:
        pg.wait_for_selector(".dcg-expressionitem", timeout=15000)
        editor_ok = True
    except Exception:
        editor_ok = False

    ok_type = False
    txt = ""
    if editor_ok:
        try:
            field = pg.locator(".dcg-mq-root-block").first
            field.click(timeout=8000)
            pg.keyboard.type("1+1")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(2500)
            ok_type = True
            txt = pg.locator(".dcg-expressionitem").first.inner_text()
        except Exception as e:
            print("输入/读取失败:", repr(e)[:200])

    calc_ok = ("1+1" in txt) and ("2" in txt)
    print("编辑器渲染:", editor_ok)
    print("输入成功:", ok_type)
    print("表达式文本:", repr(txt[:200]))
    print("1+1=>2 计算正确:", calc_ok)

    pg.screenshot(path="_verify_desmos.png")
    print()
    print("=== 统计 ===")
    print("外部请求数(应=0):", len(external))
    for u in external[:10]:
        print("  EXT", u[:90])
    print("pageerror 数:", len(page_errors))
    for e in page_errors[:10]:
        print("  ERR", e)
    print("console error 数:", len(console_errors))
    for e in console_errors[:10]:
        print("  CERR", e)
    b.close()
