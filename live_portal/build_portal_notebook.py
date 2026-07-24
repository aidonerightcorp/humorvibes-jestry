"""Generate the thin Jestry-portal notebook: dataset src -> stdlib portal -> trycloudflare URL.

Mirrors live_studio/build_live_notebook.py (the proven tunnel recipe) but serves
jestry_portal.py — stdlib only, so the kernel needs zero pip installs for the
UI. Inside Kaggle the signal instrument auto-selects the attached Gemma
checkpoint (real teacher-forced logprobs); the been-done index falls back to
the hash backend and says so in every report.

Run `python3 build_portal_notebook.py` to (re)write jestry_portal_notebook.ipynb
byte-deterministically, then push with:  kaggle kernels push -p live_portal/
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Fresh session-scoped announce channel (house rule: rotate per campaign; do not
# reuse a topic that has been committed to a public repo).
NTFY_TOPIC = "jestry-portal-live-m3w8zr52"
PORT = 8081

CELLS: list[tuple[str, str]] = [
    ("markdown",
     "# HumorVibes — Jestry Live Portal (thin launcher)\n\n"
     "Mounts the `punchline-mesh-src` dataset, boots the **Jestry** verified laugh-reuse portal "
     "(stdlib HTTP, no pip installs), and exposes it publicly through a Cloudflare quick tunnel. "
     "The `*.trycloudflare.com` URL prints below and is announced to ntfy.sh while the session "
     "runs (~8h).\n\n"
     "Inside Kaggle the S/R/E/B instrument is the attached **Gemma** checkpoint (true "
     "teacher-forced log-probabilities). The been-done precedent index runs on the offline hash "
     "backend here and labels itself accordingly — semantic embeddinggemma search is the local "
     "configuration.\n\n"
     "Charter + code: JESTRY-CHARTER-AND-CONSTITUTION-2026-07-23.md in the mounted source."),
    ("code",
     "import glob, os, re, shutil, subprocess, sys, time, urllib.request\n"
     "\n"
     "# mount layouts vary (zip-mode datasets can nest); find the source root\n"
     "# by its marker file instead of assuming the path\n"
     "hits = sorted(glob.glob('/kaggle/input/**/jestry_portal.py', recursive=True))\n"
     "assert hits, ('punchline-mesh-src source not found under /kaggle/input: '\n"
     "              + repr(sorted(glob.glob('/kaggle/input/*/*'))[:40]))\n"
     "SRC = os.path.dirname(hits[0])\n"
     "WORK = '/kaggle/working/src'\n"
     "shutil.rmtree(WORK, ignore_errors=True)\n"
     "shutil.copytree(SRC, WORK)\n"
     "os.chdir(WORK)\n"
     "os.environ['GEMMA_PROVIDER'] = 'transformers'   # attached checkpoint = real logprobs\n"
     "os.environ['JESTRY_PORTAL_PORT'] = '%d'\n"
     "print('source mounted at', WORK)\n" % PORT),
    ("code",
     "# --- in-kernel instrument calibration (background) ---\n"
     "# certifies the attached transformers Gemma for acceptance decisions;\n"
     "# jestry picks the instrument-keyed receipt up automatically when done\n"
     "cal_proc = subprocess.Popen([sys.executable, 'calibrate_gemma4.py',\n"
     "                             '--instrument', 'kaggle'],\n"
     "                            stdout=open('/kaggle/working/calibration.log', 'w'),\n"
     "                            stderr=subprocess.STDOUT, text=True)\n"
     "print('calibration launched in background (see calibration.log)')\n"),
    ("code",
     "# --- boot the stdlib portal (no pip installs) ---\n"
     "portal_proc = subprocess.Popen([sys.executable, 'jestry_portal.py'],\n"
     "                               stdout=open('/kaggle/working/portal.log', 'w'),\n"
     "                               stderr=subprocess.STDOUT, text=True)\n"
     "deadline = time.time() + 90\n"
     "ok = False\n"
     "while time.time() < deadline and not ok:\n"
     "    try:\n"
     "        urllib.request.urlopen('http://127.0.0.1:%d/api/charter', timeout=3)\n"
     "        ok = True\n"
     "    except Exception:\n"
     "        time.sleep(1.5)\n"
     "assert ok, 'portal did not answer: ' + open('/kaggle/working/portal.log').read()[-2000:]\n"
     "print('portal is answering on 127.0.0.1:%d')\n" % (PORT, PORT)),
    ("code",
     "# --- cloudflared quick tunnel ---\n"
     "CF = '/kaggle/working/cloudflared'\n"
     "urllib.request.urlretrieve(\n"
     "    'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64', CF)\n"
     "os.chmod(CF, 0o755)\n"
     "def start_tunnel():\n"
     "    return subprocess.Popen([CF, 'tunnel', '--url', 'http://127.0.0.1:%d', '--no-autoupdate'],\n"
     "                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)\n"
     "def read_url(proc, timeout=120):\n"
     "    t0, buf = time.time(), []\n"
     "    while time.time() - t0 < timeout:\n"
     "        line = proc.stdout.readline()\n"
     "        if not line:\n"
     "            time.sleep(0.2); continue\n"
     "        buf.append(line)\n"
     "        m = re.search(r'https://[a-z0-9-]+\\.trycloudflare\\.com', line)\n"
     "        if m:\n"
     "            return m.group(0), buf\n"
     "    return None, buf\n"
     "cf_proc = start_tunnel()\n"
     "url, buf = read_url(cf_proc)\n"
     "assert url, 'no tunnel URL: ' + ''.join(buf)[-2000:]\n"
     "TOPIC = '%s'\n"
     "def announce(u):\n"
     "    try:\n"
     "        req = urllib.request.Request(f'https://ntfy.sh/{TOPIC}', data=u.encode(),\n"
     "                                     headers={'Title': 'jestry portal live'})\n"
     "        urllib.request.urlopen(req, timeout=10)\n"
     "    except Exception as e:\n"
     "        print('announce failed:', e)\n"
     "announce(url)\n"
     "print('=' * 70)\n"
     "print('JESTRY PORTAL URL:', url)\n"
     "print('=' * 70)\n" % (PORT, NTFY_TOPIC)),
    ("code",
     "# --- keep-alive ~8h, re-announce hourly, restart tunnel if it drops, exit clean ---\n"
     "END = time.time() + 8 * 3600\n"
     "last_announce = time.time()\n"
     "while time.time() < END:\n"
     "    time.sleep(30)\n"
     "    if portal_proc.poll() is not None:\n"
     "        print('portal died; tail:')\n"
     "        print(open('/kaggle/working/portal.log').read()[-2000:])\n"
     "        break\n"
     "    if cf_proc.poll() is not None:\n"
     "        print('tunnel died; restarting')\n"
     "        cf_proc = start_tunnel()\n"
     "        url2, _ = read_url(cf_proc)\n"
     "        if url2:\n"
     "            url = url2; announce(url); print('new URL:', url)\n"
     "    if time.time() - last_announce > 3600:\n"
     "        announce(url); last_announce = time.time()\n"
     "print('session end; final URL was:', url)\n"
     "for p in (cf_proc, portal_proc):\n"
     "    try:\n"
     "        p.terminate()\n"
     "    except Exception:\n"
     "        pass\n"),
]


def build() -> Path:
    cells = []
    for kind, src in CELLS:
        cell: dict = {"cell_type": kind, "metadata": {}, "source": src}
        if kind == "code":
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    nb = {"nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                      "name": "python3"},
                       "language_info": {"name": "python", "version": "3.11"}},
          "cells": cells}
    out = HERE / "jestry_portal_notebook.ipynb"
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build())
