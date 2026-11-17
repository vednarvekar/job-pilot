"""Fetch jobs from free public APIs (no keys needed), filter and score them."""
import hashlib
import html
import json
import re
from pathlib import Path

import requests

DATA = Path("data")
JOBS_FILE = DATA / "jobs.json"
UA = {"User-Agent": "job-pilot/0.1 (personal job search tool)"}


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _job(source, title, company, location, url, desc, date=""):
    jid = hashlib.sha1(f"{source}|{url}".encode()).hexdigest()[:12]
    return dict(id=jid, source=source, title=title, company=company,
                location=location or "", url=url, description=_clean(desc), date=date)


def fetch_remotive(term):
    r = requests.get("https://remotive.com/api/remote-jobs", params={"search": term},
                     headers=UA, timeout=20)
    r.raise_for_status()
    return [_job("Remotive", j["title"], j["company_name"],
                 j.get("candidate_required_location") or "Remote", j["url"],
                 j["description"], j.get("publication_date", "")[:10])
            for j in r.json().get("jobs", [])]


def fetch_arbeitnow(_term):
    r = requests.get("https://www.arbeitnow.com/api/job-board-api", headers=UA, timeout=20)
    r.raise_for_status()
    return [_job("Arbeitnow", j["title"], j["company_name"],
                 ("Remote, " if j.get("remote") else "") + j.get("location", ""),
                 j["url"], j["description"], str(j.get("created_at", ""))[:10])
            for j in r.json().get("data", [])]


def fetch_remoteok(_term):
    r = requests.get("https://remoteok.com/api", headers=UA, timeout=20)
    r.raise_for_status()
    return [_job("RemoteOK", j["position"], j["company"], j.get("location") or "Remote",
                 j["url"], j.get("description", "") + " " + " ".join(j.get("tags", [])),
                 (j.get("date") or "")[:10])
            for j in r.json() if isinstance(j, dict) and j.get("position")]


SOURCES = [fetch_remotive, fetch_arbeitnow, fetch_remoteok]


def _has(text: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9+#]){re.escape(word.lower())}(?![a-z0-9+#])", text) is not None


def score(job: dict, cfg: dict) -> dict:
    text = f"{job['title']} {job['description']}".lower()
    skills = [s.lower() for s in cfg["skills"]]
    matched = [s for s in skills if _has(text, s)]
    missing = [s for s in skills if s not in matched]
    # Title relevance counts double: a search term inside the title is a strong signal.
    title = job["title"].lower()
    title_hit = any(all(w in title for w in t.lower().split()) for t in cfg["search_terms"])
    pct = 100 * len(matched) / max(1, min(len(skills), 8))
    job["score"] = min(100, round(pct * 0.7 + (30 if title_hit else 0)))
    job["matched"], job["missing"] = matched, missing
    return job


def _allowed(job: dict, cfg: dict) -> bool:
    text = f"{job['title']} {job['location']}".lower()
    if any(e.lower() in text for e in cfg.get("exclude", [])):
        return False
    locs = cfg.get("locations") or []
    return not locs or any(l.lower() in f"{text} {job['description'][:300].lower()}" for l in locs)


def load() -> dict:
    return json.loads(JOBS_FILE.read_text()) if JOBS_FILE.exists() else {}


def save(jobs: dict):
    DATA.mkdir(exist_ok=True)
    JOBS_FILE.write_text(json.dumps(jobs, indent=1))


def refresh(cfg: dict):
    """Fetch from all sources, keep relevant jobs, merge with saved state. Returns (jobs, errors)."""
    jobs, errors = load(), []
    for fetch in SOURCES:
        for term in (cfg["search_terms"] if fetch is fetch_remotive else cfg["search_terms"][:1]):
            try:
                for j in fetch(term):
                    if not _allowed(j, cfg):
                        continue
                    score(j, cfg)
                    if j["score"] < cfg.get("min_score", 0):
                        continue
                    old = jobs.get(j["id"], {})
                    j["status"] = old.get("status", "new")
                    j["resume"] = old.get("resume")
                    jobs[j["id"]] = j
            except Exception as e:  # one broken source shouldn't kill the run
                errors.append(f"{fetch.__name__}: {e}")
    save(jobs)
    return jobs, errors
