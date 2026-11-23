"""Tailor the master resume to one job using Claude."""
import re
import shutil
import subprocess
from pathlib import Path

import markdown

OUT = Path("output")

SYSTEM = """You are an expert resume writer and ATS specialist. You rewrite a candidate's \
master resume so it is tailored to one specific job posting.

Hard rules:
- NEVER invent or inflate experience, employers, dates, degrees, skills, metrics or tools. \
Use only facts present in the master resume.
- Reorder and reword to emphasise what is most relevant to the job. Drop or shrink \
irrelevant items. Mirror the job's terminology where the candidate genuinely has that skill.
- Write a 2-line summary aimed at this role. Put the most relevant skills first.
- Strong action verbs, quantified results where the master already has numbers.
- One page worth of content (about 45 lines): cut the weakest bullets rather than shrink anything.
- Keep the header exactly like the master: `# Name`, then a headline line retitled to match the \
target role (truthful: use the candidate's real experience, e.g. "AI & Automation Engineer | AWS, DevOps"), \
then the contact lines.
- Format roles/projects/education as `### Title — Org | Dates or link` (the part after ` | ` is \
right-aligned), with an italic tech-stack line under projects. Sections in this order unless the \
job favours projects first: Summary, Experience, Projects, Education, Technical Skills (grouped \
`- **Group:** items`), Certifications (only if relevant).
- Lead every bullet with a strong verb and the outcome; keep real numbers, never add new ones.
- Output ONLY the resume in Markdown (# name, ## sections, ### roles, - bullets). \
No commentary, no code fences.
- After the resume add a line `---NOTES---` followed by 2-4 short bullets: \
important job requirements the candidate does NOT clearly cover (gaps), so they can address them."""


def ask_claude(prompt: str, model: str) -> str:
    """Run the local Claude Code CLI headless, so it uses your Claude Pro/Max login (no API key)."""
    if not shutil.which("claude"):
        raise RuntimeError("Claude Code CLI not found. Install it (npm i -g @anthropic-ai/claude-code) "
                           "and run `claude` once to log in with your Claude subscription.")
    r = subprocess.run(["claude", "-p", "--model", model, "--system-prompt", SYSTEM],
                       input=prompt, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError((r.stderr or r.stdout or "claude CLI failed").strip()[:500])
    return r.stdout.strip()


def tailor(job: dict, master: str, model: str) -> dict:
    text = ask_claude(
        f"<master_resume>\n{master}\n</master_resume>\n\n"
        f"<job>\nTitle: {job['title']}\nCompany: {job['company']}\n"
        f"Location: {job['location']}\n\n{job['description'][:8000]}\n</job>", model)
    resume, _, notes = text.partition("---NOTES---")
    OUT.mkdir(exist_ok=True)
    stem = re.sub(r"[^a-z0-9]+", "-", f"{job['company']}-{job['title']}".lower()).strip("-")[:60]
    md_path, html_path = OUT / f"{stem}.md", OUT / f"{stem}.html"
    md_path.write_text(resume.strip() + "\n")
    html_path.write_text(render_html(resume.strip()))
    return {"md": str(md_path), "html": str(html_path), "notes": notes.strip()}


def render_html(md: str) -> str:
    """Markdown -> clean single-column, ATS-friendly resume page (A4, prints to one page).

    Conventions in the markdown: `# Name`, then a headline line and contact lines before the first
    `##`; `### Left text | Right text` renders as a row with the right part (dates/links) right-aligned.
    """
    md = re.sub(r"(?m)^([^-\n][^\n]*)\n(- )", r"\1\n\n\2", md.strip())  # a list needs a blank line before it
    body = markdown.markdown(md, extensions=["extra", "nl2br"])
    head, sep, rest = body.partition("<h2>")
    name = re.search(r"<h1>(.*?)</h1>", head, re.S).group(1)
    lines = [l.strip() for l in re.split(r"<br />\s*|</?p>", head.split("</h1>", 1)[1]) if l.strip()]
    head = f'<h1 class="name">{name}</h1>'
    if lines:
        head += f'<p class="headline">{lines[0]}</p>'
        head += "".join(f"<p>{re.sub(r'\s*\|\s*', ' &nbsp;·&nbsp; ', l)}</p>" for l in lines[1:])
    body = f'<header>{head}</header>' + (sep + rest if sep else "")
    body = re.sub(r"<h3>(.*?)\s\|\s(.*?)</h3>",
                  r'<h3><span class="l">\1</span><span class="r">\2</span></h3>', body)
    return f"""<!doctype html><html lang=en><meta charset=utf-8><title>Resume</title>
<style>
@page{{size:A4;margin:9mm 13mm}}
:root{{--ink:#1a1a1a;--mut:#555;--acc:#1f3a5f}}
*{{box-sizing:border-box}}
body{{font:9pt/1.25 "Helvetica Neue",Calibri,Arial,sans-serif;color:var(--ink);max-width:800px;
margin:24px auto;padding:0 22px;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
header{{text-align:center;margin-bottom:6px}}
h1.name{{font-size:22pt;letter-spacing:.14em;text-transform:uppercase;margin:0 0 2px;font-weight:700}}
p.headline{{font-size:10.6pt;font-weight:600;color:var(--acc);margin:0 0 3px}}
header p{{margin:1px 0;color:var(--mut);font-size:9pt}}
a{{color:inherit;text-decoration:none}}
h2{{font-size:9.8pt;letter-spacing:.12em;text-transform:uppercase;color:var(--acc);
border-bottom:1.2px solid var(--acc);padding-bottom:1px;margin:6px 0 3px;break-after:avoid}}
h3{{display:flex;justify-content:space-between;align-items:baseline;gap:12px;font-size:10pt;
margin:4px 0 1px;font-weight:700;break-after:avoid}}
h3 .r{{font-weight:400;color:var(--mut);font-size:9pt;white-space:nowrap}}
p{{margin:2px 0}} em{{color:var(--mut)}}
ul{{margin:2px 0 3px;padding-left:15px}} li{{margin:1px 0}}
h2+ul{{list-style:none;padding-left:0}} h2+ul li{{margin:2px 0}}
li,h3{{break-inside:avoid}}
@media print{{body{{margin:0;padding:0;max-width:none}}}}
</style>{body}</html>"""
