#!/usr/bin/env python3
"""Real-browser acceptance test for the Jestry portal.

The portal ships an empty ``<nav>`` and builds every tab client-side, so curl
proves nothing about what a judge actually sees. This drives a real headless
Chrome over the DevTools pipe (forge_studio/cdp.py, zero dependencies): it
clicks through every tab, screenshots each one, records JS exceptions, console
errors and failed network requests, cross-checks rendered numbers against the
portal's own API, exercises the interactive forms with real queries, and
re-renders at a phone viewport to catch horizontal overflow.

Failures are reported, never swallowed: the exit code is non-zero if any tab
throws, any request fails, or any cross-check disagrees.

    python3 jestry_portal.py &                 # or JESTRY_PORTAL_PORT=8099
    python3 browser_test_portal.py --port 8099

Receipt: jestry_out/browser_test_portal.json, screenshots in browser_test_out/.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "forge_studio"))

from cdp import Chrome, CDPError  # noqa: E402

OUT_DIR = HERE / "browser_test_out"
RECEIPT = HERE / "jestry_out" / "browser_test_portal.json"


def api(port: int, path: str) -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=30) as r:
        return json.loads(r.read())


def drain(chrome: Chrome) -> dict[str, list]:
    """Pull page-level failures out of the CDP event backlog."""
    found: dict[str, list] = {"exceptions": [], "failed_requests": [], "console_errors": []}
    for ev in list(chrome._events):
        method = ev.get("method", "")
        p = ev.get("params", {})
        if method == "Runtime.exceptionThrown":
            det = p.get("exceptionDetails", {})
            text = det.get("exception", {}).get("description") or det.get("text", "")
            found["exceptions"].append(text[:300])
        elif method == "Network.loadingFailed":
            # canceled preloads are not failures a user would see
            if not p.get("canceled"):
                found["failed_requests"].append(
                    f"{p.get('type', '?')}: {p.get('errorText', '?')}")
        elif method == "Network.responseReceived":
            resp = p.get("response", {})
            if int(resp.get("status", 200)) >= 400:
                found["failed_requests"].append(f"HTTP {resp['status']} {resp.get('url', '')[:120]}")
    for level, text in chrome.console:
        if level in ("error", "assert"):
            found["console_errors"].append(text[:300])
    return found


def click_tab(chrome: Chrome, index: int) -> None:
    chrome.eval(
        "(() => {const els = Array.from(document.querySelectorAll('#nav button, #nav a'));"
        f"const el = els[{index}]; if (el) el.click(); return true;}})()")


def index_of(tabs: list[dict], needle: str) -> int:
    for t in tabs:
        if needle in t["label"].lower():
            return t["index"]
    return 0


def settle(chrome: Chrome, seconds: float = 1.2) -> None:
    """Give fetch-driven panes time to paint (portal renders after api())."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        chrome.eval("1", ret=True)
        time.sleep(0.15)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8099)
    args = ap.parse_args()
    base = f"http://127.0.0.1:{args.port}/"
    OUT_DIR.mkdir(exist_ok=True)

    census = api(args.port, "/api/census")
    dash = api(args.port, "/api/dashboard")

    report: dict = {
        "receipt_type": "browser_test_portal",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "url": base,
        "api_truth": {"digest": census["digest"], "total_cards": census["census"]["total_cards"]},
        "tabs": [],
        "interactions": [],
        "viewports": [],
        "failures": [],
    }

    with Chrome(width=1280, height=900) as c:
        c._scall("Network.enable")
        c._scall("Log.enable")
        c.goto(base)
        settle(c, 2.0)

        nav_labels = c.eval(
            "Array.from(document.querySelectorAll('#nav button, #nav a'))"
            ".map(e => e.textContent.trim()).filter(Boolean)")
        if not nav_labels:
            report["failures"].append("nav rendered no tabs (client-side build failed)")
        report["nav_labels"] = nav_labels

        for i, label in enumerate(nav_labels):
            click_tab(c, i)
            settle(c, 2.2)          # panes that autoload fetch on first show
            info = c.eval(
                "(() => {const m = document.querySelector('#main');"
                "return {text_len: (m ? m.innerText.trim().length : 0),"
                " svg: document.querySelectorAll('#main svg').length,"
                " svg_children: Array.from(document.querySelectorAll('#main svg'))"
                "   .reduce((n, s) => n + s.querySelectorAll('*').length, 0),"
                " buttons: document.querySelectorAll('#main button').length,"
                " scroll_w: document.documentElement.scrollWidth,"
                " client_w: document.documentElement.clientWidth};})()")
            shot = OUT_DIR / f"tab_{i:02d}_{label.lower().replace(' ', '_').replace('?', '')[:24]}.png"
            shot.write_bytes(c.screenshot_bytes())
            tab = {"index": i, "label": label, **info, "screenshot": shot.name}
            if info["text_len"] < 40:
                report["failures"].append(f"tab '{label}' rendered almost no text ({info['text_len']} chars)")
            report["tabs"].append(tab)

        # --- cross-check: the dashboard's numbers must be the API's numbers ----
        dash_tab = next((t for t in report["tabs"] if "dash" in t["label"].lower()), None)
        if dash_tab:
            if dash_tab["svg"] == 0 or dash_tab["svg_children"] < 10:
                report["failures"].append(
                    f"dashboard SVG missing or empty (svg={dash_tab['svg']}, "
                    f"children={dash_tab['svg_children']})")
            c.eval("(() => {const els = Array.from(document.querySelectorAll('#nav button, #nav a'));"
                   f"const el = els[{dash_tab['index']}]; if (el) el.click(); return true;}})()")
            settle(c, 1.4)
            body = c.eval("document.querySelector('#main').innerText")
            total = str(census["census"]["total_cards"])
            pretty = f"{census['census']['total_cards']:,}"
            shown = total in body or pretty in body
            report["interactions"].append(
                {"check": "dashboard shows API card total", "expected": pretty, "found": shown})
            if not shown:
                report["failures"].append(f"dashboard does not display the card total {pretty}")

        # --- interaction: real precedent query through the real index ---------
        # every pane lives in the DOM at once and show(i) only toggles a class,
        # so a control must be made VISIBLE before it is driven: innerText of a
        # hidden pane is "" and a test that skips this reads empty output from a
        # perfectly healthy portal (2026-07-24: that false alarm cost a rerun)
        query = "Even the most skilled monkey falls from the tree sometimes."
        click_tab(c, index_of(report["tabs"], "been done"))
        settle(c, 0.8)
        ok = c.eval(
            "(() => {const box = document.querySelector('#bd'); const btn = document.querySelector('#bdbtn');"
            f"if (!box || !btn) return false; box.value = {json.dumps(query)};"
            "btn.click(); return true;})()")
        if ok:
            # a real embed + 23k-item scan measured ~10s against the live API,
            # so poll to completion rather than guessing a settle window
            out = ""
            saw_pending = False
            deadline = time.time() + 45
            while time.time() < deadline:
                settle(c, 1.0)
                out = c.eval("(document.querySelector('#bdout') || {}).innerText || ''")
                if "embedding the query" in out:
                    saw_pending = True      # the visitor gets feedback, not a dead button
                elif out:
                    break
            report["interactions"].append(
                {"check": "slow query shows a pending state", "saw_pending": saw_pending})
            if not saw_pending:
                report["failures"].append(
                    "been-done ran with no pending feedback (button looks dead for ~10s)")
            hit = ("원숭이" in out) or ("猿" in out) or ("monkey" in out.lower())
            (OUT_DIR / "interaction_beendone.png").write_bytes(c.screenshot_bytes())
            report["interactions"].append(
                {"check": "been-done returns cross-lingual neighbours", "query": query,
                 "chars": len(out), "cross_lingual_hit": hit, "excerpt": out[:240]})
            if len(out) < 20:
                report["failures"].append("been-done returned an empty pane")
        else:
            report["failures"].append("been-done form controls (#bd/#bdbtn) not found")

        # --- interaction: census button must agree with the API digest --------
        click_tab(c, index_of(report["tabs"], "registry"))
        settle(c, 0.8)
        ok = c.eval("(() => {const b = document.querySelector('#cenbtn'); if (!b) return false;"
                    "b.click(); return true;})()")
        if ok:
            settle(c, 2.5)
            out = c.eval("(document.querySelector('#regout') || {}).innerText || ''")
            agrees = census["digest"] in out
            report["interactions"].append(
                {"check": "census pane shows the API registry digest",
                 "digest": census["digest"], "agrees": agrees})
            if not agrees:
                report["failures"].append(
                    f"census pane digest disagrees with /api/census ({census['digest']})")

        desktop = drain(c)
        report["desktop_page_errors"] = desktop
        for key in ("exceptions", "failed_requests", "console_errors"):
            for item in desktop[key]:
                report["failures"].append(f"{key}: {item}")

        report["viewports"].append({"name": "desktop", "w": 1280, "h": 900,
                                    "no_h_overflow": all(t["scroll_w"] <= t["client_w"] + 1
                                                         for t in report["tabs"])})

    # --- phone viewport: a judge on a phone must not scroll sideways ----------
    with Chrome(width=390, height=844) as c:
        c._scall("Network.enable")
        c.goto(base)
        settle(c, 2.5)
        m = c.eval("({scroll_w: document.documentElement.scrollWidth,"
                   " client_w: document.documentElement.clientWidth,"
                   " text_len: (document.querySelector('#main')||{innerText:''}).innerText.length})")
        (OUT_DIR / "viewport_phone.png").write_bytes(c.screenshot_bytes())
        overflow = m["scroll_w"] > m["client_w"] + 1
        report["viewports"].append({"name": "phone", "w": 390, "h": 844,
                                    "no_h_overflow": not overflow, **m})
        if overflow:
            report["failures"].append(
                f"phone viewport scrolls horizontally ({m['scroll_w']} > {m['client_w']})")

    report["dashboard_api_keys"] = sorted(dash.keys())
    report["passed"] = not report["failures"]
    RECEIPT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"tabs tested: {len(report['tabs'])} -> {[t['label'] for t in report['tabs']]}")
    for it in report["interactions"]:
        print("  check:", json.dumps(it, ensure_ascii=False)[:180])
    print(f"screenshots: {len(list(OUT_DIR.glob('*.png')))} in {OUT_DIR.name}/")
    if report["failures"]:
        print(f"\nFAILURES ({len(report['failures'])}):")
        for f in report["failures"]:
            print("  -", f)
    else:
        print("\nALL BROWSER CHECKS PASSED")
    print("receipt ->", RECEIPT)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
