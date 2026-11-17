"""job-pilot: find jobs that match you and generate a tailored resume for each."""
import json
import os
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file

import jobs as jobstore
import tailor as tailor_mod

app = Flask(__name__)


def cfg() -> dict:
    p = Path("config.json")
    if not p.exists():
        p = Path("config.example.json")
    return json.loads(p.read_text())


def master() -> str:
    p = Path("master_resume.md")
    if not p.exists():
        abort(400, "Create master_resume.md first (see master_resume.example.md).")
    return p.read_text()


@app.get("/")
def index():
    all_jobs = sorted(jobstore.load().values(), key=lambda j: -j["score"])
    return render_template("index.html", jobs=all_jobs)


@app.post("/refresh")
def refresh():
    jobs, errors = jobstore.refresh(cfg())
    return jsonify(count=len(jobs), errors=errors)


@app.post("/status/<jid>")
def status(jid):
    jobs = jobstore.load()
    if jid not in jobs:
        abort(404)
    jobs[jid]["status"] = request.json["status"]
    jobstore.save(jobs)
    return jsonify(ok=True)


@app.post("/tailor/<jid>")
def tailor(jid):
    jobs = jobstore.load()
    if jid not in jobs:
        abort(404)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return jsonify(error="Set ANTHROPIC_API_KEY before starting the app."), 400
    try:
        res = tailor_mod.tailor(jobs[jid], master(), cfg().get("model", "claude-sonnet-5-5"))
    except Exception as e:
        return jsonify(error=str(e)), 500
    jobs[jid]["resume"] = res
    jobstore.save(jobs)
    return jsonify(res)


@app.get("/resume/<jid>")
def resume(jid):
    job = jobstore.load().get(jid)
    if not job or not job.get("resume"):
        abort(404)
    return send_file(Path(job["resume"]["html"]).resolve())


@app.get("/resume/<jid>.md")
def resume_md(jid):
    job = jobstore.load().get(jid)
    if not job or not job.get("resume"):
        abort(404)
    return send_file(Path(job["resume"]["md"]).resolve(), as_attachment=True)


if __name__ == "__main__":
    app.run(debug=False, port=5000)
