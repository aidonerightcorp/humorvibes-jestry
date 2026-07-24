#!/usr/bin/env python3
"""Generate the thin live-studio notebook: dataset src -> Streamlit -> trycloudflare URL.

The notebook is deliberately thin: all product code ships in the Kaggle dataset
taylorsamarel/punchline-mesh-src (and the GitHub repo mirror); this kernel just
mounts, serves, and tunnels. The public URL is announced via ntfy.sh (batch
kernels expose no logs mid-run) and printed in the log for the archived run.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NTFY_TOPIC = "punchline-mesh-live-k7q2xa41"  # bake: poll https://ntfy.sh/<topic>/json?poll=1

CELLS = [
    {
        "cell_type": "markdown",
        "id": "cell-01",
        "metadata": {},
        "source": (
            "# HumorVibes — Live Studio (thin launcher)\n\n"
            "Mounts the `punchline-mesh-src` dataset, starts the Streamlit humor studio with a real "
            "Gemma (measured surprise/resolution/efficiency/bad-surprise off the logits), and exposes "
            "it publicly through a Cloudflare quick tunnel. The `*.trycloudflare.com` URL prints below "
            "and is announced to ntfy.sh while the session runs (~8h).\n\n"
            "Theory + code: see THEORY.md / WRITEUP.md inside the mounted source."
        ),
    },
    {
        "cell_type": "code",
        "id": "cell-02",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": (
            "import glob, os, re, shutil, subprocess, sys, time, urllib.request\n\n"
            "# --- locate mounted source (dataset zip is auto-extracted under /kaggle/input) ---\n"
            "apps = glob.glob('/kaggle/input/**/app.py', recursive=True)\n"
            "assert apps, 'punchline-mesh-src dataset not attached'\n"
            "SRC = os.path.dirname(apps[0])\n"
            "DST = '/kaggle/working/pm'\n"
            "shutil.copytree(SRC, DST, dirs_exist_ok=True)\n"
            "os.chdir(DST)\n"
            "print('source:', SRC, '->', DST)\n\n"
            "subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'streamlit'], check=True)\n\n"
            "# --- point the studio at the attached Gemma; measured signals need real logits ---\n"
            "gcfg = [p for p in glob.glob('/kaggle/input/**/config.json', recursive=True) if 'gemma' in p.lower()]\n"
            "assert gcfg, 'gemma model not attached'\n"
            "os.environ['GEMMA_MODEL_PATH'] = os.path.dirname(gcfg[0])\n"
            "os.environ['GEMMA_PROVIDER'] = 'transformers'\n"
            "print('gemma:', os.environ['GEMMA_MODEL_PATH'])\n\n"
            "# Optional hosted-LLM panel keys via Kaggle user secrets (add them in the\n"
            "# notebook editor: Add-ons -> Secrets). Missing secrets are fine — the panel\n"
            "# simply lists itself in dry-run mode and Gemma stays the core engine.\n"
            "try:\n"
            "    from kaggle_secrets import UserSecretsClient\n"
            "    usc = UserSecretsClient()\n"
            "    for name in ('NVIDIA_API_KEY', 'OLLAMA_CLOUD_API_KEY', 'OLLAMA_API_KEY', 'ADVISOR_LLM_API_KEY',\n"
            "                 'MISTRAL_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'):\n"
            "        try:\n"
            "            os.environ[name] = usc.get_secret(name)\n"
            "            print('panel key loaded:', name)\n"
            "        except Exception:\n"
            "            pass\n"
            "except Exception:\n"
            "    pass"
        ),
    },
    {
        "cell_type": "code",
        "id": "cell-03",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": (
            "# --- start the studio ---\n"
            "st_proc = subprocess.Popen(\n"
            "    [sys.executable, '-m', 'streamlit', 'run', 'app.py',\n"
            "     '--server.port', '8501', '--server.address', '0.0.0.0',\n"
            "     '--server.headless', 'true', '--browser.gatherUsageStats', 'false'],\n"
            "    stdout=open('/kaggle/working/streamlit.log', 'w'), stderr=subprocess.STDOUT)\n"
            "for i in range(120):\n"
            "    try:\n"
            "        urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2)\n"
            "        print(f'streamlit up after {i+1}s'); break\n"
            "    except Exception:\n"
            "        time.sleep(1)\n"
            "else:\n"
            "    print(open('/kaggle/working/streamlit.log').read()[-3000:]); raise RuntimeError('streamlit never came up')"
        ),
    },
    {
        "cell_type": "code",
        "id": "cell-04",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": (
            "# --- cloudflared quick tunnel ---\n"
            "CF = '/kaggle/working/cloudflared'\n"
            "urllib.request.urlretrieve(\n"
            "    'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64', CF)\n"
            "os.chmod(CF, 0o755)\n"
            "cf_proc = subprocess.Popen([CF, 'tunnel', '--url', 'http://127.0.0.1:8501', '--no-autoupdate'],\n"
            "                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)\n"
            "url = None\n"
            "deadline = time.time() + 120\n"
            "buf = []\n"
            "while time.time() < deadline and url is None:\n"
            "    line = cf_proc.stdout.readline()\n"
            "    if not line: time.sleep(0.2); continue\n"
            "    buf.append(line)\n"
            "    m = re.search(r'https://[a-z0-9-]+\\.trycloudflare\\.com', line)\n"
            "    if m: url = m.group(0)\n"
            "assert url, 'no tunnel URL: ' + ''.join(buf)[-2000:]\n"
            f"TOPIC = '{NTFY_TOPIC}'\n"
            "def announce(u):\n"
            "    try:\n"
            "        req = urllib.request.Request(f'https://ntfy.sh/{TOPIC}', data=u.encode(),\n"
            "                                     headers={'Title': 'punchline-mesh live'})\n"
            "        urllib.request.urlopen(req, timeout=10)\n"
            "    except Exception as e:\n"
            "        print('announce failed:', e)\n"
            "announce(url)\n"
            "print('=' * 70)\n"
            "print('LIVE STUDIO URL:', url)\n"
            "print('=' * 70)"
        ),
    },
    {
        "cell_type": "code",
        "id": "cell-05",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": (
            "# --- keep-alive ~8h, re-announce hourly, restart tunnel if it drops, exit clean ---\n"
            "END = time.time() + 8 * 3600\n"
            "last_announce = time.time()\n"
            "while time.time() < END:\n"
            "    time.sleep(30)\n"
            "    if st_proc.poll() is not None:\n"
            "        print('streamlit died; tail:'); print(open('/kaggle/working/streamlit.log').read()[-2000:]); break\n"
            "    if cf_proc.poll() is not None:\n"
            "        print('tunnel died; restarting')\n"
            "        cf_proc = subprocess.Popen([CF, 'tunnel', '--url', 'http://127.0.0.1:8501', '--no-autoupdate'],\n"
            "                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)\n"
            "        t0 = time.time(); url2 = None\n"
            "        while time.time() - t0 < 120 and url2 is None:\n"
            "            line = cf_proc.stdout.readline()\n"
            "            m = re.search(r'https://[a-z0-9-]+\\.trycloudflare\\.com', line or '')\n"
            "            if m: url2 = m.group(0)\n"
            "        if url2: url = url2; announce(url); print('new URL:', url)\n"
            "    if time.time() - last_announce > 3600:\n"
            "        announce(url); last_announce = time.time()\n"
            "print('session end; final URL was:', url)\n"
            "for p in (cf_proc, st_proc):\n"
            "    try: p.terminate()\n"
            "    except Exception: pass"
        ),
    },
]


def main() -> None:
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "cells": CELLS,
    }
    (HERE / "live_notebook.ipynb").write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print("wrote", HERE / "live_notebook.ipynb")


if __name__ == "__main__":
    main()
