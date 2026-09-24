"""Offline HTML report. Dataset paths are HTML-escaped; no remote assets."""

from html import escape


def render_html(report):
    summary = report["summary"]
    cards = "".join(f'<div class="card"><strong>{value}</strong><span>{escape(key.replace("_", " "))}</span></div>'
                    for key, value in summary.items())
    rows = "".join('<tr>' + ''.join(f'<td>{escape(str(item[field]))}</td>'
                                  for field in ("severity", "code", "path", "message")) + '</tr>'
                   for item in report["issues"])
    if not rows:
        rows = '<tr><td colspan="4">No findings for the configured checks.</td></tr>'
    total = sum(report["class_pixels"].values()) or 1
    bars = "".join(f'<div class="barrow"><span>Class {escape(key)}</span>'
                   f'<div class="track"><div class="bar" style="width:{100*value/total:.2f}%"></div></div>'
                   f'<span>{value:,} pixels</span></div>' for key, value in report["class_pixels"].items())
    config = report["configuration"]
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mask Dataset Audit</title><style>
body{{font:16px/1.6 system-ui,sans-serif;color:#203047;background:#f4f7fb;margin:0}}
main{{max-width:1120px;margin:auto;padding:40px 24px}}h1{{font-size:36px;margin-bottom:0}}
.muted{{color:#53657c}}.cards{{display:flex;flex-wrap:wrap;gap:14px;margin:28px 0}}
.card{{background:white;border:1px solid #dbe4ef;border-radius:12px;padding:18px;flex:1;min-width:120px}}
.card strong{{display:block;font-size:32px;color:#155a94}}.card span{{display:block;font-size:14px}}
section{{background:white;border:1px solid #dbe4ef;border-radius:12px;padding:24px;margin-top:22px}}
.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #e3eaf2;vertical-align:top;overflow-wrap:anywhere}}
th{{background:#f4f7fb}}.barrow{{display:grid;grid-template-columns:80px 1fr 150px;gap:12px;align-items:center;margin:12px 0}}
.track{{height:16px;background:#edf2f7;border-radius:8px;overflow:hidden}}.bar{{height:100%;background:#277cb7}}
@media(max-width:600px){{main{{padding:20px 12px}}.barrow{{grid-template-columns:60px 1fr}}.barrow>span:last-child{{grid-column:2}}}}
</style></head><body><main><p class="muted">LOCAL · READ-ONLY · NO GPU</p><h1>Mask Dataset Audit</h1>
<p class="muted">Check segmentation data before spending time on training.</p><div class="cards">{cards}</div>
<section><h2>Label distribution</h2><p>Labels: {escape(str(config['labels']))} · Ignore: {escape(str(config['ignore']))}</p>{bars}
<p class="muted">Counts include every readable index mask, including unpaired and mismatched masks. Ignored and unknown pixels are excluded from these bars.</p></section>
<section><h2>Findings</h2><div class="scroll"><table><thead><tr><th>Severity</th><th>Check</th><th>Path</th><th>Details</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<p class="muted">Exact duplicates do not establish patient identity. This report cannot rule out near-duplicate images or patient-level leakage. Reports include filenames; review before sharing.</p>
</main></body></html>'''
