"""Build a self-contained review page from review-data.json.

The owner flips each domain between delete / promo / keep / skip and sets a
label, then copies the decisions block back into the chat. Nothing is trashed
or unsubscribed until those decisions come back.

Choices persist in localStorage, and the output is also shown in a
pre-selected <textarea> because clipboard writes fail silently in sandboxed
viewers.

Usage:
  python -m gmail_org review-page --data review-data.json --out review.html
"""
from __future__ import annotations

import argparse
import html
import json

from .config import load_rules

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mailbox review</title>
<style>
:root{--bg:#fafaf9;--fg:#1c1917;--mut:#78716c;--line:#e7e5e4;--card:#fff;--del:#dc2626;--promo:#d97706;--keep:#16a34a;--skip:#64748b}
@media (prefers-color-scheme:dark){:root{--bg:#1c1917;--fg:#f5f5f4;--mut:#a8a29e;--line:#44403c;--card:#292524}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}h1{font-size:20px;margin:8px 0}
.sum{color:var(--mut);margin-bottom:12px}.bar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
input[type=search]{flex:1;min-width:180px;padding:8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
.row{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:6px 0;display:grid;grid-template-columns:1fr auto;gap:6px}
.dom{font-weight:600}.meta,.subj{color:var(--mut);font-size:12px}.subj{grid-column:1/-1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.why{font-size:12px}.mixed{color:var(--promo);font-weight:600}
.seg{display:flex;gap:2px}.seg button{border:1px solid var(--line);background:transparent;color:var(--fg);padding:4px 8px;border-radius:5px;cursor:pointer;font-size:12px}
.seg button.on[data-v=delete]{background:var(--del);color:#fff}.seg button.on[data-v=promo]{background:var(--promo);color:#fff}
.seg button.on[data-v=keep]{background:var(--keep);color:#fff}.seg button.on[data-v=skip]{background:var(--skip);color:#fff}
.lbl{grid-column:1/-1}.lbl select{padding:3px;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:4px;font-size:12px}
textarea{width:100%;height:160px;font:12px ui-monospace,monospace;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:8px}
.btn{padding:8px 12px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
@media (max-width:600px){.row{grid-template-columns:1fr}}
</style></head><body><main>
<h1>Mailbox review</h1>
<div class="sum" id="sum"></div>
<p class="why"><b>delete</b> = unsubscribe (if active) and move backlog to Trash · <b>promo</b> = stay subscribed, label, skip inbox ·
<b>keep</b> = stay subscribed, label, stay in inbox · <b>skip</b> = don't touch. Starred mail is never trashed.</p>
<div class="bar"><input type="search" id="q" placeholder="Filter domains"><button class="btn" id="reset">Reset to suggestions</button></div>
<div id="list"></div>
<h2 style="font-size:16px">Decisions (paste this back into the chat)</h2>
<button class="btn" id="copy">Copy</button>
<textarea id="out" readonly></textarea>
</main>
<script>
const DATA = __DATA__;
const LABELS = __LABELS__;
const KEY = "mailbox-review-v1";
let st = {};
try { st = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const get = d => st[d.domain] || {v: d.suggested, label: d.label || ""};
function save(){ try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} render(); }
function esc(s){ return String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function render(){
  const q = document.getElementById("q").value.toLowerCase();
  const list = document.getElementById("list"); list.innerHTML = "";
  const counts = {delete:0,promo:0,keep:0,skip:0}; let msgs = 0;
  DATA.forEach(d => {
    const s = get(d); counts[s.v]++; if (s.v === "delete") msgs += d.count;
    if (q && !d.domain.includes(q)) return;
    const el = document.createElement("div"); el.className = "row";
    el.innerHTML = `<div><div class="dom">${esc(d.domain)} <span class="meta">${d.count} msgs · latest ${esc(d.latest||"?")} · ${d.active?"active":"dormant"} · ${d.addresses.length} address(es)</span></div>
      <div class="why">${d.mixed?'<span class="mixed">Mixed: sends records too. </span>':""}${esc(d.why)}</div></div>
      <div class="seg">${["delete","promo","keep","skip"].map(v=>`<button data-v="${v}" class="${s.v===v?"on":""}">${v}</button>`).join("")}</div>
      <div class="lbl">Label: <select>${["",...LABELS].map(l=>`<option ${l===s.label?"selected":""}>${esc(l)}</option>`).join("")}</select></div>
      <div class="subj">${esc((d.subjects||[]).slice(0,3).join(" · "))}</div>`;
    el.querySelectorAll(".seg button").forEach(b => b.onclick = () => { st[d.domain] = {...get(d), v: b.dataset.v}; save(); });
    el.querySelector("select").onchange = e => { st[d.domain] = {...get(d), label: e.target.value}; save(); };
    list.appendChild(el);
  });
  document.getElementById("sum").textContent = `${DATA.length} domains · delete ${counts.delete} (${msgs} messages) · promo ${counts.promo} · keep ${counts.keep} · skip ${counts.skip}`;
  const dec = {}; DATA.forEach(d => { const s = get(d); (dec[s.v] = dec[s.v] || []).push(s.label ? `${d.domain} -> ${s.label}` : d.domain); });
  const out = document.getElementById("out");
  out.value = "DECISIONS v1\\n" + ["delete","promo","keep","skip"].map(k => `${k.toUpperCase()} (${(dec[k]||[]).length}):\\n` + (dec[k]||[]).join("\\n")).join("\\n\\n");
}
document.getElementById("q").oninput = render;
document.getElementById("reset").onclick = () => { st = {}; save(); };
document.getElementById("copy").onclick = () => { const o = document.getElementById("out"); o.select();
  (navigator.clipboard ? navigator.clipboard.writeText(o.value) : Promise.reject()).catch(() => document.execCommand && document.execCommand("copy")); };
render(); document.getElementById("out").select();
</script></body></html>
"""


def build(data: list[dict], labels: list[str]) -> str:
    safe = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return PAGE.replace("__DATA__", safe).replace("__LABELS__", json.dumps(sorted(set(labels))))


def parse_decisions(text: str) -> dict[str, list[dict]]:
    """Parse the pasted DECISIONS block back into {state: [{domain, label}]}."""
    out: dict[str, list[dict]] = {k: [] for k in ("delete", "promo", "keep", "skip")}
    cur = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("DECISIONS"):
            continue
        head = line.split(" ", 1)[0].lower()
        if head in out and line.endswith(":"):
            cur = head
            continue
        if cur:
            dom, _, label = (p.strip() for p in line.partition("->"))
            out[cur].append({"domain": html.unescape(dom), "label": label or None})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build review.html from review-data.json")
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rules")
    a = ap.parse_args(argv)
    rules = load_rules(a.rules)
    data = json.load(open(a.data, encoding="utf-8"))
    for d in data:
        d.setdefault("label", rules.get("sender_labels", {}).get(d["domain"], ""))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(build(data, list(rules["labels"].values())))
    print(f"wrote {a.out} ({len(data)} domains)")


if __name__ == "__main__":
    main()
