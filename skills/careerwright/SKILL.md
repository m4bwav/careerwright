---
name: careerwright
description: "Use for the job hunt after a lead is found: tailor a resume and cover letter to one posting (keyword gaps, ATS lint), render a JSON Resume to plain one-column text, track applications through stages with follow-up dates, write company prep notes, and run STAR mock interviews on askwright pages; cr.py runs each step. Use on 'tailor my resume for this job', 'write a cover letter for', 'is my resume ATS-safe', 'track this application', 'what follow-ups are due', 'prep me for the interview at', 'mock interview me'. Not for finding leads (job-lead-scout) or sending anything."
---

# careerwright

From a lead to an offer: tailor, apply, track, prepare. Run as `python "${CLAUDE_PLUGIN_ROOT}/scripts/cr.py" <command>`.

Personal data lives in `CAREERWRIGHT_HOME` (default `~/.careerwright`): the person's own history files, `applications.json`, and one folder per application (`apps/<id>-<company-slug>/` with the posting, tailored resume, letter and prep notes). Read the home's README first if it has one. Never put personal data in this plugin's folder.

Hard rule: never submit an application, send an email or message, or sign in to a job site. Draft, save, and tell the person what is ready to send.

## Tailor a resume to one posting

1. Save the posting text as `posting.txt` in the application folder (ask for it if only a link is given and fetching fails).
2. `cr.py keywords posting.txt <master resume>` lists the posting's terms and which the resume lacks.
3. Write the tailored resume from the person's own history files, not from the posting: reorder bullets so the matching work comes first, use the posting's words for things the person has really done, and leave out a missing term rather than claim it. List the gaps that stay so the person can say if any is true.
4. `cr.py lint tailored.md` (or `.docx`): fix every error (tables, columns, text boxes, no email). One column, standard headings, dates on each role. Run `keywords` again and report the coverage before and after.
5. If the person keeps a JSON Resume, `cr.py render resume.json --out resume.md` gives the plain one-column text to start from.

## Cover letter

Three short paragraphs, under 300 words: why this company (one concrete fact from their site or posting, checked), the two pieces of the person's work that match the posting's top needs with numbers, and a plain close. No "I am writing to express my interest". Save as `letter.md` beside the resume. Details: [references/letters.md](references/letters.md).

## Track applications

- `cr.py track add --company X --title Y --link URL [--stage applied]`; `track move <id> --stage screen --note "..."` sets the next follow-up date by stage (applied 7 days, screen 5, interview 3, offer 2; `--follow-up DATE` overrides).
- `cr.py track list` (open ones), `track due --days 2` (follow-ups due and wishlist entries untouched 14 days).
- `cr.py track import-leads leads.md` pulls `**Company — Title** ... link ... status: x` lines from a lead list into the wishlist, skipping rejected ones and duplicates.
- Stages: wishlist, applied, screen, interview, offer, accepted, rejected, withdrawn, archived. Never delete an entry; move it to a closed stage.
- When a follow-up is due, draft the email in the application folder and say it is ready; the person sends it.

## Interview prep

1. Company notes (`prep.md` in the application folder): what they sell and to whom, size and funding or public status, recent news from the last six months, the team's stack from the posting and their engineering blog, interview process reports, and three questions to ask them. Cite each fact with its link and date. Template: [references/prep.md](references/prep.md).
2. Mock interview: `cr.py interview --role "<title>" --posting posting.txt --count 5 --out q.json` writes STAR questions as askwright `text` questions. Start a set with askwright's `ask.py new`, `ask.py add <set> q.json`, lint, serve, and give the link. When answered, read them back, run `cr.py score answer.txt` on each, and return a short critique and a tighter version to rehearse out loud (spoken rehearsal beats reading).
3. Behavioural questions follow the posting's stated values; technical ones follow its named tools.

## Maintenance

Evergreen unit: research in [RESEARCH.md](../../RESEARCH.md), changes in [CHANGELOG.md](../../CHANGELOG.md), lessons in [LEARNINGS.md](../../LEARNINGS.md), state in [evergreen.json](../../evergreen.json), evals in [TESTS.md](../../TESTS.md). On 'refresh careerwright', run evergreen-refresh on this unit.
