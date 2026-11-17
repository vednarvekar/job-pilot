# Job Pilot

Personal tool: finds jobs matching your skills and writes a tailored resume for each one.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json            # edit: search terms, skills, locations
cp master_resume.example.md master_resume.md  # edit: your real, complete resume
export ANTHROPIC_API_KEY=sk-ant-...
python app.py                                 # open http://localhost:5000
```

## Use
1. **Find jobs** – pulls from Remotive, Arbeitnow and RemoteOK (free, no keys), filters by your
   locations/excludes, and scores each job by how many of your skills it mentions.
2. **Tailor resume** – Claude rewrites `master_resume.md` for that job (never inventing facts) and
   lists gaps you should address. Open it and use *Print → Save as PDF*.
3. Mark jobs applied/skipped to keep the list clean.

Put *everything* you've done in `master_resume.md` – the tailor picks what's relevant per job.
Always read the output before sending it.
