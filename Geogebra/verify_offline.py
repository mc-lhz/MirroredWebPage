# -*- coding: utf-8 -*-
"""
Offline verifier for the GeoGebra mirror.

Uses REAL mouse clicks (never programmatic .click()) to open the Suite app
picker and switch through every available mode. Also runs a GeoGebra API
smoke test and checks for external requests when offline.

Usage:
  python verify_offline.py          # file://
  python verify_offline.py http     # http://127.0.0.1:8138
  python verify_offline.py http --online  # do not abort external requests
"""

import os, sys, pathlib
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
INDEX = HERE / "index.html"
MODES = ["Graphing", "3D Calculator", "Geometry", "CAS", "Probability", "Scientific"]

mode = sys.argv[1] if len(sys.argv) > 1 else "file"
online = "--online" in sys.argv
URL = INDEX.as_uri() if mode == "file" else "http://127.0.0.1:8138/index.html"


def main():
    errs, ext, failed = [], [], []
    results = []
    smoke = None
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1366, "height": 768})
        pg = ctx.new_page()

        if not online:

            def route(rt):
                u = rt.request.url
                if (
                    u.startswith(("file://", "data:", "blob:", "about:"))
                    or "127.0.0.1" in u
                ):
                    rt.continue_()
                else:
                    ext.append(u)
                    rt.abort()

            pg.route("**/*", route)

        pg.on(
            "pageerror",
            lambda e: errs.append("pageerror: " + str(e).split("\n")[0][:150]),
        )
        pg.on(
            "console",
            lambda m: (
                errs.append("console: " + m.text[:140]) if m.type == "error" else None
            ),
        )
        pg.on("requestfailed", lambda r: failed.append(r.url[-120:]))

        print(f"[load] {URL}")
        pg.goto(URL, wait_until="load", timeout=90000)
        pg.wait_for_selector(".suiteAppPickerButton", timeout=60000)
        pg.wait_for_timeout(6000)

        btn = pg.locator(".suiteAppPickerButton").first

        def popup_open():
            return pg.evaluate("""() => {
              const e = document.querySelector('.appPickerPopup');
              if (!e) return false;
              const s = getComputedStyle(e);
              return s.display !== 'none' && s.visibility !== 'hidden';
            }""")

        def open_picker():
            if popup_open():
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(400)
            btn.click(timeout=15000)
            pg.wait_for_timeout(900)
            if not popup_open():
                btn.click(timeout=15000)
                pg.wait_for_timeout(900)
            return popup_open()

        for want in MODES:
            try:
                if not open_picker():
                    raise RuntimeError("picker popup did not open")
                row = pg.locator(".appPickerRow", has_text=want).first
                if row.count() == 0:
                    raise RuntimeError("row not found")
                row.click(timeout=15000)
                pg.wait_for_timeout(5000)
                label = (btn.inner_text() or "").strip().replace("\n", " ")
                ok = want.lower().replace(" ", "") in label.lower().replace(" ", "")
                results.append((want, ok, label))
                print(
                    f"  {'OK  ' if ok else 'FAIL'} click '{want}' -> picker now reads '{label}'"
                )
            except Exception as e:
                results.append((want, False, f"EXC {e}"))
                print(f"  FAIL click '{want}': {str(e).splitlines()[0][:160]}")
                try:
                    pg.keyboard.press("Escape")
                except Exception:
                    pass

        try:
            open_picker()
            pg.locator(".appPickerRow", has_text="Graphing").first.click(timeout=15000)
            pg.wait_for_timeout(5000)
            smoke = pg.evaluate("""() => {
              const a = window.ggbApplet;
              if (!a || !a.evalCommand) return 'no applet api';
              a.evalCommand('f(x)=x^2');
              return String(a.getValue('f(2)'));
            }""")
        except Exception as e:
            smoke = "EXC " + str(e)[:120]

        pg.screenshot(path=str(HERE / "_verify_final.png"))
        b.close()

    passed = sum(1 for _, ok, _ in results if ok)
    print("\n" + "=" * 60)
    print(f"mode switches (REAL clicks) : {passed}/{len(MODES)}")
    print(f"API smoke  f(x)=x^2 -> f(2) : {smoke}   (expect 4)")
    print(f"pageerrors / console errors : {len(errs)}")
    for e in dict.fromkeys(errs):
        print("    ", e)
    print(f"external requests blocked   : {len(ext)}")
    for u in dict.fromkeys(ext):
        print("    ", u[:110])
    print(f"failed requests             : {len(failed)}")
    for u in dict.fromkeys(failed):
        print("    ", u)
    print("=" * 60)
    good = passed == len(MODES) and not errs and not ext and not failed and smoke == "4"
    print("RESULT:", "PASS" if good else "NEEDS WORK")
    return 0 if good else 1


sys.exit(main())
