# careerwright

![careerwright banner](.github/images/banner.jpg)

The job hunt after the lead, as an agent plugin. Give it a posting and your resume and it shows which of the posting's terms your resume lacks, checks the resume will survive an applicant tracking system, helps write a tailored resume and cover letter from your real history, tracks every application with follow-up dates, writes company prep notes, and runs STAR mock interviews on askwright pages.

It never sends anything. Applications, emails and sign-ins stay with you.

## What it does

- **Keyword gaps**: `cr.py keywords posting.txt resume.md` lists posting terms present and missing, with a coverage score.
- **ATS lint**: `cr.py lint resume.docx` flags tables, multi-column layouts, text boxes, missing headings, contact details and dates.
- **Render**: `cr.py render resume.json --out resume.md` turns a [JSON Resume](https://jsonresume.org) into plain one-column markdown.
- **Tracker**: `cr.py track add|move|list|due` keeps applications in a JSON file with stages, history and follow-up dates; `track import-leads leads.md` pulls a markdown lead list into the wishlist.
- **Mock interviews**: `cr.py interview --role "Backend Engineer" --posting posting.txt --out q.json` writes STAR questions for an askwright page; `cr.py score answer.txt` gives a rough STAR check of a written answer.

Your data lives in `CAREERWRIGHT_HOME` (default `~/.careerwright`), outside the plugin. Needs only Python 3.9+.

## Install

```
/plugin marketplace add m4bwav/careerwright
/plugin install careerwright
```

Or run the script directly: `python scripts/cr.py --help`.

## Develop

`python -m pytest -q`. Rules: [AGENTS.md](AGENTS.md).

## Licence

MIT.
