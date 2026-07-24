"""Jestry live portal: the verified laugh-reuse loop behind one web page.

Stdlib only (http.server + threads) so it boots anywhere — a laptop, a Kaggle
kernel behind a trycloudflare quick tunnel, a demo booth — with zero pip
installs. Endpoints mirror the CLI; every run writes the same receipts.

Tabs: Dashboard (receipts-driven charts), Run, Been done?, Registry, Charter,
Ledger. Charts follow the dataviz doctrine: single-hue bars for magnitude,
fixed categorical slots for identity, status colors (with glyphs, never color
alone) for accept/reject, hairline grid, text in text tokens, tooltips on every
mark, and a table view under each chart. The categorical/dark palette passed
the six-check validator against this page's surface (#151923).

    python3 jestry_portal.py                # http://127.0.0.1:8081
    JESTRY_PORTAL_PORT=9000 python3 jestry_portal.py

The portal never hides provider truth: each response carries the instrument
name, measured flags, and the been-done backend, exactly as the receipts do.
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jestry import (  # noqa: E402
    ACCEPTANCE_LEVELS, CHARTER_VERSION, FUNNEL_STAGES, LAWS, MOTTO,
    BitRegistry, Jestry, WorkSpec,
)

_LOCK = threading.RLock()   # re-entrant: /api/run holds it across get_jestry()
_JESTRY: Jestry | None = None


def get_jestry() -> Jestry:
    global _JESTRY
    with _LOCK:
        if _JESTRY is None:
            _JESTRY = Jestry()
        return _JESTRY


def dashboard_data() -> dict:
    """Aggregate every ledger into chart-ready rows (server-side, no pandas)."""
    j = get_jestry()
    receipts = j.receipts.read_all()
    accepted = [r for r in receipts if r.get("outcome", {}).get("accepted")]
    route_mix: dict[str, int] = {}
    funnel: dict[str, int] = {k: 0 for k in FUNNEL_STAGES if k != "discovered"}
    cands: list[dict] = []
    for r in receipts:
        kind = r.get("route", {}).get("kind", "?")
        route_mix[kind] = route_mix.get(kind, 0) + 1
        for k in funnel:
            funnel[k] += r.get("funnel", {}).get(k, 0)
        for c in r.get("candidates", []):
            cands.append({"laugh": c.get("laugh_score"),
                          "accepted": bool(c.get("accepted")),
                          "measured": bool(c.get("measured")),
                          "text": (c.get("text") or "")[:90]})
    census = j.registry.census()
    harvests: list[dict] = []
    hp = j.out_dir / "harvest_receipts.jsonl"
    if hp.exists():
        agg: dict[str, int] = {}
        for line in hp.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            agg[rec.get("lane", "?")] = agg.get(rec.get("lane", "?"), 0) + int(rec.get("new", 0))
        harvests = [{"lane": k, "new": v} for k, v in sorted(agg.items(), key=lambda kv: -kv[1])]
    sweep: list[dict] = []
    sp = j.out_dir / "instrument_sweep.jsonl"
    if sp.exists():
        for line in sp.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("receipt_type") != "instrument_sweep" or "rows" not in rec:
                continue
            sweep.append({"config": rec["config"],
                          "jokes_R": [r["R"] for r in rec["rows"] if r["kind"] == "joke"],
                          "ctrl_R": [r["R"] for r in rec["rows"] if r["kind"] == "control"],
                          "certifiable": bool(rec.get("certifiable_R") or rec.get("certifiable_R_uc"))})
    cal = {}
    for cp in sorted(j.out_dir.glob("*calibration*.json")):
        try:
            c = json.loads(cp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        row = {"certified": bool(c.get("certified")), "instrument": c.get("instrument"),
               "model": c.get("model"), "ts": c.get("ts")}
        if row["certified"] or not cal:      # a certified instrument wins the hero line
            cal = row
    vec = j.north_star_vector()
    return {
        "hero": {"accepted_outcomes": len(accepted), "runs": len(receipts)},
        "tiles": [
            {"label": "registry cards", "value": census.get("total_cards", 0)},
            {"label": "verified-or-better bits", "value": census.get("accepted_or_better", 0)},
            {"label": "harvested records", "value": sum(h["new"] for h in harvests)},
            {"label": "measured-signal runs", "value": vec.get("measured_signal_runs", 0)},
            {"label": "groaners ledgered", "value": vec.get("groaners_recorded", 0)},
            {"label": "zero-model accepts", "value": vec.get("zero_model_call_accepts", 0)},
        ],
        "route_mix": [{"kind": k, "runs": v} for k, v in sorted(route_mix.items(), key=lambda kv: -kv[1])],
        "funnel": [{"stage": k, "value": funnel[k]} for k in funnel],
        "census": [{"kind": k, "value": v} for k, v in sorted(census.items(), key=lambda kv: -kv[1])
                   if k not in ("total_cards", "accepted_or_better")],
        "harvest": harvests,
        "cands": cands[-48:],
        "sweep": sweep[-12:],
        "calibration": cal,
        "posteriors": [{"frame": f[:52], "mean": round(m, 3)} for f, m in j.laughloop.serving_order()[:8]],
    }


PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jestry — verified laugh-reuse portal</title>
<style>
  :root { color-scheme: dark;
    --surface:#0f1115; --surface-1:#151923; --line:#262a33; --grid:#232833;
    --ink:#e6e6e6; --ink-2:#9aa3b2; --ink-3:#7d8799;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181;
    --good:#0ca30c; --serious:#ec835a; }
  body { margin:0; font:15px/1.5 system-ui, sans-serif; background:var(--surface); color:var(--ink); }
  header { padding:18px 22px 8px; border-bottom:1px solid var(--line); }
  header h1 { margin:0; font-size:20px; } header p { margin:4px 0 10px; color:var(--ink-2); font-size:13px; }
  nav button { background:#1a1e27; color:#cfd6e4; border:1px solid #2c3140; border-radius:8px 8px 0 0;
               padding:8px 14px; margin-right:6px; cursor:pointer; font-size:14px; }
  nav button.on { background:#2b3140; color:#fff; }
  main { padding:18px 22px; max-width:1100px; }
  section { display:none; } section.on { display:block; }
  textarea, input, select { width:100%; box-sizing:border-box; background:var(--surface-1); color:var(--ink);
    border:1px solid #2c3140; border-radius:8px; padding:9px; font:14px/1.4 inherit; margin:4px 0 10px; }
  label { font-size:12px; color:var(--ink-2); text-transform:uppercase; letter-spacing:.06em; }
  .row { display:grid; grid-template-columns:1fr 1fr; gap:0 16px; }
  .go { background:#3b5bdb; border:none; color:#fff; padding:10px 18px; border-radius:8px;
        font-size:15px; cursor:pointer; }
  .go[disabled] { opacity:.5; }
  pre { background:#12151d; border:1px solid var(--line); border-radius:10px; padding:14px;
        white-space:pre-wrap; word-break:break-word; font-size:12.5px; max-height:520px; overflow:auto; }
  .card { background:var(--surface-1); border:1px solid #2c3140; border-radius:10px; padding:12px 14px; margin:10px 0; }
  .accept { border-left:4px solid var(--good); } .reject { border-left:4px solid var(--serious); }
  .tag { display:inline-block; background:#1f2430; border-radius:6px; padding:1px 8px; margin:0 6px 4px 0;
         font-size:12px; color:#9fb3d1; }
  small { color:var(--ink-3); }
  /* dashboard */
  .hero { display:flex; align-items:baseline; gap:14px; margin:6px 0 2px; }
  .hero .n { font-size:52px; font-weight:600; line-height:1; }
  .hero .cap { color:var(--ink-2); font-size:14px; }
  .tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:12px 0 4px; }
  .tile { background:var(--surface-1); border:1px solid #2c3140; border-radius:10px; padding:10px 12px; }
  .tile .v { font-size:22px; font-weight:600; } .tile .l { font-size:12px; color:var(--ink-2); }
  .charts { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; margin-top:12px; }
  figure.viz { margin:0; background:var(--surface-1); border:1px solid #2c3140; border-radius:10px; padding:12px 14px; }
  figure.viz figcaption { font-size:13px; color:var(--ink); font-weight:600; margin-bottom:6px; }
  figure.viz .sub { font-size:12px; color:var(--ink-2); font-weight:400; }
  .legend { display:flex; gap:14px; font-size:12px; color:var(--ink-2); margin:4px 0 2px; }
  .legend .k { display:inline-flex; align-items:center; gap:5px; }
  .sw { width:10px; height:10px; border-radius:3px; display:inline-block; }
  details.tbl { margin-top:6px; } details.tbl summary { font-size:12px; color:var(--ink-3); cursor:pointer; }
  details.tbl table { width:100%; border-collapse:collapse; font-size:12px; margin-top:6px; }
  details.tbl td, details.tbl th { border-top:1px solid var(--line); padding:3px 6px; text-align:left;
    color:var(--ink-2); font-variant-numeric: tabular-nums; }
  #tip { position:fixed; pointer-events:none; background:#0b0d12; border:1px solid #2c3140; color:var(--ink);
         padding:6px 9px; border-radius:8px; font-size:12.5px; display:none; z-index:10; max-width:340px; }
  figure.viz { overflow:hidden; }
  figure.viz svg { max-width:100%; display:block; }
  svg text { font:11.5px system-ui, sans-serif; fill:var(--ink-2); }
  svg .val { fill:var(--ink); font-variant-numeric: tabular-nums; }
</style>
<header>
  <h1>Jestry <small>— verified laugh-reuse &amp; construction portal (charter v__CHARTER__)</small></h1>
  <p>__MOTTO__</p>
  <nav id="nav"></nav>
</header>
<main id="main"></main>
<div id="tip"></div>
<script>
const TABS = ["Dashboard", "Run", "Been done?", "Registry", "Charter", "Ledger"];
const nav = document.getElementById("nav"), main = document.getElementById("main");
TABS.forEach((t,i) => {
  const b = document.createElement("button"); b.textContent = t;
  b.onclick = () => show(i); nav.appendChild(b);
  const s = document.createElement("section"); s.id = "tab"+i; main.appendChild(s);
});
function show(i){ [...nav.children].forEach((b,j)=>b.classList.toggle("on", i===j));
  [...main.children].forEach((s,j)=>s.classList.toggle("on", i===j));
  if (i===0) loadDash(); }
async function api(path, body){
  const r = await fetch(path, body ? {method:"POST", headers:{"Content-Type":"application/json"},
                                      body: JSON.stringify(body)} : {});
  return r.json();
}
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* ---------- tooltip ---------- */
const tip = document.getElementById("tip");
function tipOn(ev, html){ tip.innerHTML = html; tip.style.display = "block"; tipMove(ev); }
function tipMove(ev){ const pad = 14;
  tip.style.left = Math.min(ev.clientX + pad, innerWidth - tip.offsetWidth - 8) + "px";
  tip.style.top  = Math.min(ev.clientY + pad, innerHeight - tip.offsetHeight - 8) + "px"; }
function tipOff(){ tip.style.display = "none"; }

/* ---------- chart helpers (SVG, mark specs from the dataviz doctrine) ---------- */
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs, parent){ const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function barPath(x, y, w, h){          // horizontal bar: square baseline, 4px rounded data-end
  const r = Math.min(4, w, h/2);
  return `M${x},${y} h${Math.max(0,w-r)} a${r},${r} 0 0 1 ${r},${r} v${h-2*r} a${r},${r} 0 0 1 -${r},${r} h-${Math.max(0,w-r)} z`;
}
function hbars(host, rows, {color=getComputedStyle(document.body).getPropertyValue("--s1"),
                            colors=null, fmt=(v)=>v, unit=""}={}){
  const W = host.clientWidth - 28 || 300, BH = 18, GAP = 8, LAB = 130;
  const H = rows.length * (BH + GAP) + 6;
  const max = Math.max(...rows.map(r => r.value), 1);
  const svg = el("svg", {width: W, height: H, role: "img"}, host);
  const gx = el("g", {}, svg);
  [0.5, 1].forEach(f => el("line", {x1: LAB + (W-LAB-46)*f, x2: LAB + (W-LAB-46)*f, y1: 0, y2: H-4,
    stroke: "var(--grid)", "stroke-width": 1}, gx));
  rows.forEach((r, i) => {
    const y = i * (BH + GAP), w = Math.max(2, (W - LAB - 46) * r.value / max);
    el("text", {x: LAB - 8, y: y + BH*0.72, "text-anchor": "end"}, svg)
      .textContent = r.label.length > 17 ? r.label.slice(0, 16) + "…" : r.label;
    const p = el("path", {d: barPath(LAB, y, w, BH), fill: (colors ? colors[i % colors.length] : color)}, svg);
    const t = el("text", {x: LAB + w + 6, y: y + BH*0.72, class: "val"}, svg);
    t.textContent = fmt(r.value);
    p.addEventListener("mousemove", tipMove);
    p.addEventListener("mouseenter", ev => tipOn(ev, `<b>${esc(r.label)}</b><br>${esc(fmt(r.value))} ${esc(unit)}`));
    p.addEventListener("mouseleave", tipOff);
  });
}
function dotStrip(host, rows){          // laugh scores: status colors + glyph legend
  const W = host.clientWidth - 28 || 300, H = 96, PAD = 34;
  const svg = el("svg", {width: W, height: H, role: "img"}, host);
  [0, 25, 50, 75, 100].forEach(v => {
    const x = PAD + (W - PAD - 12) * v / 100;
    el("line", {x1: x, x2: x, y1: 8, y2: H - 22, stroke: "var(--grid)", "stroke-width": 1}, svg);
    el("text", {x: x, y: H - 8, "text-anchor": "middle"}, svg).textContent = v;
  });
  rows.forEach((r, i) => {
    if (r.laugh == null) return;
    const x = PAD + (W - PAD - 12) * Math.max(0, Math.min(100, r.laugh)) / 100;
    const y = 16 + (i % 5) * 13;
    const c = el("circle", {cx: x, cy: y, r: 5, fill: r.accepted ? "var(--good)" : "var(--serious)",
                            stroke: "var(--surface-1)", "stroke-width": 2}, svg);
    c.addEventListener("mousemove", tipMove);
    c.addEventListener("mouseenter", ev => tipOn(ev,
      `<b>${r.accepted ? "✓ accepted" : "✕ rejected"}</b> · laugh ${r.laugh}` +
      `${r.measured ? "" : " · <i>unmeasured</i>"}<br>${esc(r.text)}`));
    c.addEventListener("mouseleave", tipOff);
  });
}
function tableView(host, rows, cols){
  const d = document.createElement("details"); d.className = "tbl";
  d.innerHTML = `<summary>table view</summary>`;
  const t = document.createElement("table");
  t.innerHTML = `<tr>${cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr>` +
    rows.map(r => `<tr>${cols.map(c => `<td>${esc(r[c])}</td>`).join("")}</tr>`).join("");
  d.appendChild(t); host.appendChild(d);
}
function fig(parent, title, sub){
  const f = document.createElement("figure"); f.className = "viz";
  f.innerHTML = `<figcaption>${esc(title)}${sub ? ` <span class="sub">— ${esc(sub)}</span>` : ""}</figcaption>`;
  parent.appendChild(f); return f;
}

/* ---------- Dashboard tab ---------- */
async function loadDash(){
  const d = await api("/api/dashboard");
  const t0 = document.getElementById("tab0");
  t0.innerHTML = "";
  const hero = document.createElement("div"); hero.className = "hero";
  hero.innerHTML = `<span class="n">${d.hero.accepted_outcomes}</span>
    <span class="cap">accepted outcomes across ${d.hero.runs} receipted runs · calibration
    ${d.calibration.certified ? "CERTIFIED (" + esc(d.calibration.instrument) + ")"
                              : "not certified — acceptance stays gated"}</span>`;
  t0.appendChild(hero);
  const tiles = document.createElement("div"); tiles.className = "tiles";
  d.tiles.forEach(x => { const e = document.createElement("div"); e.className = "tile";
    e.innerHTML = `<div class="v">${x.value}</div><div class="l">${esc(x.label)}</div>`; tiles.appendChild(e); });
  t0.appendChild(tiles);
  const grid = document.createElement("div"); grid.className = "charts"; t0.appendChild(grid);

  // create ALL figure shells first: auto-fit track widths depend on item
  // count, so measuring clientWidth before every card exists renders the
  // early charts against a 1-item (full-width) track and they overflow
  const fFunnel = fig(grid, "Contribution funnel", "stage sums across all receipts");
  const fMix = fig(grid, "Route mix", "which rung answered each request");
  const fLaugh = fig(grid, "Candidate laugh scores", "per candidate, live runs");
  const fCensus = fig(grid, "Registry census", "body-free capability cards by kind");
  const fHarvest = fig(grid, "Harvest yield", "new licensed records by lane");
  const fPost = d.posteriors.length ?
    fig(grid, "LaughLoop serving posteriors", "governed bandit, promoted state only") : null;
  const fSweep = d.sweep.length ?
    fig(grid, "Instrument sweep", "challenger configs vs reference set") : null;

  hbars(fFunnel, d.funnel.map(x => ({label: x.stage, value: x.value})), {unit: "events"});
  tableView(fFunnel, d.funnel, ["stage", "value"]);

  const slots = ["--s1","--s3","--s2","--s4","--s5"].map(v => `var(${v})`);
  const order = ["replay_accepted","replay_program","remix_corpus","compose_residual","frontier_compose","ABSTAIN"];
  const mix = d.route_mix.slice().sort((a,b) => order.indexOf(a.kind) - order.indexOf(b.kind));
  hbars(fMix, mix.map(x => ({label: x.kind, value: x.runs})), {colors: mix.map(x =>
    slots[Math.max(0, order.indexOf(x.kind)) % slots.length]), unit: "runs"});
  tableView(fMix, d.route_mix, ["kind", "runs"]);

  fLaugh.insertAdjacentHTML("beforeend", `<div class="legend">
    <span class="k"><span class="sw" style="background:var(--good)"></span>✓ accepted</span>
    <span class="k"><span class="sw" style="background:var(--serious)"></span>✕ rejected</span></div>`);
  dotStrip(fLaugh, d.cands);
  tableView(fLaugh, d.cands.map(c => ({laugh: c.laugh, accepted: c.accepted ? "yes" : "no",
    measured: c.measured ? "yes" : "no", text: c.text})), ["laugh", "accepted", "measured", "text"]);

  hbars(fCensus, d.census.map(x => ({label: x.kind, value: x.value})), {unit: "cards"});
  tableView(fCensus, d.census, ["kind", "value"]);

  hbars(fHarvest, d.harvest.map(x => ({label: x.lane, value: x.new})), {unit: "records"});
  tableView(fHarvest, d.harvest, ["lane", "new"]);

  if (fPost){
    hbars(fPost, d.posteriors.map(x => ({label: x.frame, value: x.mean})),
          {fmt: v => v.toFixed(3), unit: "posterior mean"});
    tableView(fPost, d.posteriors, ["frame", "mean"]);
  }
  if (fSweep){
    tableView(fSweep, d.sweep.map(s => ({config: `${s.config.model} ${s.config.layout} ${s.config.wrap}`,
      jokes_R: s.jokes_R.join(" / "), controls_R: s.ctrl_R.join(" / "),
      certifiable: s.certifiable ? "YES" : "no"})), ["config", "jokes_R", "controls_R", "certifiable"]);
    fSweep.querySelector("details").open = true;
  }
}

/* ---------- Run tab ---------- */
document.getElementById("tab1").innerHTML = `
  <label>request</label><textarea id="req" rows="2">Make a joke about AI project managers</textarea>
  <div class="row">
    <div><label>audience</label><input id="aud" value="NYC tech meetup"></div>
    <div><label>format</label><select id="fmt"></select></div>
    <div><label>personas (comma-sep, B-gate)</label><input id="per" value="NYC tech meetup, retired farmers"></div>
    <div><label>preferences</label><input id="pref" value="smart, not mean"></div>
  </div>
  <button class="go" id="runbtn">Compile route &amp; run</button>
  <span id="runstate" style="margin-left:10px;color:var(--ink-2)"></span>
  <div id="runout"></div>`;
api("/api/formats").then(d => { const f = document.getElementById("fmt");
  d.formats.forEach(k => { const o = document.createElement("option"); o.textContent = k; f.appendChild(o); }); });
document.getElementById("runbtn").onclick = async () => {
  const b = document.getElementById("runbtn"); b.disabled = true;
  const st = document.getElementById("runstate");
  st.textContent = "compiling route, generating, measuring S/R/E/B (can take minutes)…";
  const d = await api("/api/run", {request: req.value, audience: aud.value, format: fmt.value,
                                   personas: per.value, preferences: pref.value});
  b.disabled = false; st.textContent = "";
  const o = document.getElementById("runout");
  const oc = d.outcome || {};
  let html = `<div class="card"><b>route</b> ${esc(d.route?.kind)} <small>(${esc(d.route?.compat)})</small>
    — ${esc(d.route?.reason)}<br><small>instrument: ${esc(d.oracle_usage?.provider)} ·
    model ${esc(d.oracle_usage?.model)} · nll calls ${d.oracle_usage?.nll_calls}</small></div>`;
  (d.candidates || []).forEach(c => {
    html += `<div class="card ${c.accepted ? "accept" : "reject"}">${esc(c.text)}<br>
      <small>laugh ${c.laugh_score ?? "n/a"} · measured ${c.measured} · ${esc(c.failure_mode ?? "")}</small></div>`; });
  if (oc.accepted) html += `<div class="card accept"><b>ACCEPTED</b> at <b>${esc(oc.acceptance_level)}</b>
    → ${esc(oc.bit_id)}<br>${esc(oc.text)}</div>`;
  else html += `<div class="card reject"><b>NOT ACCEPTED</b> — ${esc(oc.reason ?? "")}</div>`;
  if (d.precedent) html += `<div class="card"><b>been done?</b> ${esc(d.precedent.verdict)}
    <small>(backend ${esc(d.precedent.backend)})</small></div>`;
  html += `<pre>${esc(JSON.stringify(d.funnel))}\\nwall ${d.wall_s}s · receipt appended to jestry_out/receipts.jsonl</pre>`;
  o.innerHTML = html;
};

/* ---------- Been done tab ---------- */
document.getElementById("tab2").innerHTML = `
  <label>candidate joke / phrase</label>
  <textarea id="bd" rows="2">Even the most senior monkey falls out of the tree sometimes.</textarea>
  <button class="go" id="bdbtn">Check precedent</button>
  <div id="bdout"></div>`;
document.getElementById("bdbtn").onclick = async () => {
  const d = await api("/api/beendone", {text: bd.value});
  let html = `<div class="card"><b>${esc(d.verdict)}</b><br><small>backend ${esc(d.backend)} ·
    semantic ${d.semantic} · indexed ${d.indexed_items} items</small>
    ${d.note ? `<br><small>${esc(d.note)}</small>` : ""}</div>`;
  (d.surface_hits || []).slice(0,5).forEach(h => {
    html += `<div class="card"><span class="tag">${esc(h.language)}</span>
      <span class="tag">${h.score}</span> ${esc(h.text)}<br>
      <small>${esc(h.source)} · ${esc(h.license)}</small></div>`; });
  document.getElementById("bdout").innerHTML = html;
};

/* ---------- Registry tab ---------- */
document.getElementById("tab3").innerHTML = `
  <button class="go" id="cenbtn">Census</button>
  <label style="margin-top:10px">search supply</label><input id="q" value="political joke for a mixed audience">
  <button class="go" id="qbtn">Search cards</button><div id="regout"></div>`;
document.getElementById("cenbtn").onclick = async () => {
  const d = await api("/api/census");
  document.getElementById("regout").innerHTML = `<pre>${esc(JSON.stringify(d, null, 2))}</pre>`; };
document.getElementById("qbtn").onclick = async () => {
  const d = await api("/api/search", {request: q.value});
  let html = "";
  (d.cards || []).forEach(c => { html += `<div class="card"><span class="tag">${esc(c.kind)}</span>
    <span class="tag">${esc(c.acceptance_level)}</span> <b>${esc(c.bit_id)}</b><br>${esc(c.one_line)}</div>`; });
  document.getElementById("regout").innerHTML = html || "<small>no hits</small>"; };

/* ---------- Charter tab ---------- */
api("/api/charter").then(d => {
  let html = `<p><i>${esc(d.motto)}</i></p>`;
  d.laws.forEach((l,i) => html += `<div class="card"><b>Law ${i+1} — ${esc(l[0])}</b><br>
    <small>${esc(l[1])}</small></div>`);
  html += `<pre>funnel: ${d.funnel.join(" → ")}\\nacceptance: ${d.acceptance.join(" < ")}</pre>`;
  document.getElementById("tab4").innerHTML = html; });

/* ---------- Ledger tab ---------- */
document.getElementById("tab5").innerHTML = `
  <button class="go" id="stbtn">North-star vector</button>
  <button class="go" id="grbtn" style="background:#5f3dc4">Groaner ledger</button>
  <div id="ledout"></div>`;
document.getElementById("stbtn").onclick = async () => {
  const d = await api("/api/stats");
  document.getElementById("ledout").innerHTML = `<pre>${esc(JSON.stringify(d, null, 2))}</pre>`; };
document.getElementById("grbtn").onclick = async () => {
  const d = await api("/api/groaners");
  let html = "";
  (d.groaners || []).forEach(g => html += `<div class="card reject">${esc(g.joke)}<br>
    <small>${esc(g.failure_mode)}</small></div>`);
  document.getElementById("ledout").innerHTML = html || "<small>no groaners yet</small>"; };

show(0);
</script>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj) -> None:
        self._send(200, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt: str, *args) -> None:  # quiet, kernel logs are precious
        pass

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            page = PAGE.replace("__CHARTER__", CHARTER_VERSION).replace("__MOTTO__", MOTTO)
            self._send(200, page.encode("utf-8"), "text/html")
        elif self.path == "/api/charter":
            self._json({"motto": MOTTO, "laws": [list(l) for l in LAWS],
                        "funnel": list(FUNNEL_STAGES), "acceptance": list(ACCEPTANCE_LEVELS)})
        elif self.path == "/api/formats":
            from formats import FORMATS
            self._json({"formats": list(FORMATS)})
        elif self.path == "/api/census":
            reg = get_jestry().registry
            self._json({"digest": reg.digest(), "census": reg.census()})
        elif self.path == "/api/stats":
            self._json(get_jestry().north_star_vector())
        elif self.path == "/api/groaners":
            self._json({"groaners": get_jestry().groaners.tail(12)})
        elif self.path == "/api/dashboard":
            self._json(dashboard_data())
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self) -> None:
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, b'{"error":"bad json"}')
            return
        if self.path == "/api/search":
            spec = WorkSpec.from_request(str(body.get("request", "")),
                                         audience=str(body.get("audience", "")))
            cards = get_jestry().registry.search(spec, limit=12)
            self._json({"cards": [c.to_dict() for c in cards]})
        elif self.path == "/api/run":
            spec = WorkSpec.from_request(
                str(body.get("request", "")), audience=str(body.get("audience", "")),
                format_key=str(body.get("format", "one_liner")),
                preferences=str(body.get("preferences", "")),
                personas=str(body.get("personas", "")),
                consent=bool(body.get("consent", False)),
                candidates=int(body.get("candidates", 3)))
            with _LOCK:
                receipt = get_jestry().run(spec, live=not bool(body.get("offline")))
            self._json(receipt)
        elif self.path == "/api/beendone":
            from precedent import quick_check
            self._json(quick_check(str(body.get("text", "")), live=True))
        elif self.path == "/api/laugh":
            with _LOCK:
                entry = get_jestry().laughloop.record_laughter(
                    str(body.get("frame", "")), float(body.get("seconds", 0.0)))
            self._json(entry)
        elif self.path == "/api/promote":
            with _LOCK:
                self._json(get_jestry().laughloop.promote())
        else:
            self._send(404, b'{"error":"not found"}')


def serve(port: int | None = None) -> None:
    port = port or int(os.environ.get("JESTRY_PORTAL_PORT", "8081"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Jestry portal on http://127.0.0.1:{port}  (charter v{CHARTER_VERSION})")
    httpd.serve_forever()


if __name__ == "__main__":
    serve()
