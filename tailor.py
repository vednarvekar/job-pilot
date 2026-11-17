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
- One page worth of content. Keep the header (name/contact) exactly as in the master.
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
    body = markdown.markdown(md, extensions=["extra"])
    return f"""<!doctype html><meta charset=utf-8><title>Resume</title>
<style>
body{{font:11pt/1.4 Georgia,serif;max-width:780px;margin:30px auto;padding:0 20px;color:#111}}
h1{{font-size:22pt;margin:0}} h2{{font-size:12pt;text-transform:uppercase;letter-spacing:.06em;
border-bottom:1px solid #444;margin:16px 0 6px}} h3{{font-size:11pt;margin:10px 0 2px}}
ul{{margin:2px 0 6px;padding-left:20px}} p{{margin:3px 0}}
@media print{{body{{margin:0}} @page{{margin:14mm}}}}
</style>{body}"""
