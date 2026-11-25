#!/usr/bin/env python3
"""careerwright CLI: job-hunt checks and records, standard library only.

Commands:
  keywords POSTING RESUME     posting terms present in or missing from a resume
  lint RESUME                 ATS-safety checks (columns, tables, sections, contact)
  render RESUME.json          JSON Resume to single-column markdown
  track add|move|list|due     application tracker (JSON file)
  track import-leads LEADS.md add leads from a markdown list to the tracker
  interview                   STAR mock-interview questions as an askwright file

Data lives in CAREERWRIGHT_HOME (default ~/.careerwright). Exit 2 is a usage or
validation error.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

STAGES = ["wishlist", "applied", "screen", "interview", "offer", "accepted", "rejected", "withdrawn", "archived"]
CLOSED = {"accepted", "rejected", "withdrawn", "archived"}
FOLLOW_UP_DAYS = {"applied": 7, "screen": 5, "interview": 3, "offer": 2}

STOP = set("""a about above after all also an and any are as at be been being both but by can could did do does
doing each etc for from had has have having how if in into is it its just may more most must no nor not of on one
or other our ours out over own per plus same should so some such than that the their them then there these they
this those through to too under up us very was we well were what when where which while who whom why will with
within would you your yours able across along among around ability strong experience experienced years year work
working team teams role job company candidate candidates including include includes new using use used like
preferred required requirements responsibilities qualifications skills skill plus bonus great good excellent
knowledge understanding familiarity proven demonstrated ideal looking join help build building make ensure
day days time based within across multiple various related relevant e.g i.e""".split())

ROLE_WORDS = set("""senior junior staff principal lead head chief director manager engineer engineers engineering
developer developers software backend frontend full stack fullstack platform remote hybrid onsite architect
requirements responsibilities about benefits we you our""".split())

TECH_RE =re.compile(r"\.?[A-Za-z][A-Za-z0-9+#.\-/]*[A-Za-z0-9+#]|[A-Za-z]")


def die(msg):
    print("error: " + msg, file=sys.stderr)
    sys.exit(2)


def home():
    return Path(os.environ.get("CAREERWRIGHT_HOME") or Path.home() / ".careerwright")


def read_text(path):
    p = Path(path)
    if not p.exists():
        die(f"no such file: {path}")
    if p.suffix.lower() == ".docx":
        return docx_text(p)[0]
    if p.suffix.lower() == ".json":
        try:
            return render_md(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError as e:
            die(f"{path}: bad JSON: {e}")
    return p.read_text(encoding="utf-8", errors="replace")


def docx_text(p):
    """Return (text, info) from a .docx: paragraphs joined by newlines, plus table and column counts."""
    try:
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError):
        die(f"{p}: not a readable .docx")
    info = {
        "tables": len(re.findall(r"<w:tbl>", xml)),
        "columns": max([int(n) for n in re.findall(r'<w:cols [^>]*w:num="(\d+)"', xml)] or [1]),
        "text_boxes": len(re.findall(r"<w:txbxContent", xml)),
    }
    paras = []
    for para in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
        runs = re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", para)
        paras.append("".join(runs))
    text = "\n".join(paras)
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
        text = text.replace(a, b)
    return text, info


# ---------- keywords ----------

def terms(text):
    words = [w.rstrip(".-/").lstrip("-/").lower() for w in TECH_RE.findall(text)]
    words = [w for w in words if w and w not in STOP and not w.isdigit() and len(w) > 1]
    uni = Counter(words)
    bi = Counter(f"{a} {b}" for a, b in zip(words, words[1:]))
    return uni, bi


def tools(text):
    """Named technologies: tokens with + # or a dot, acronyms, CamelCase, or capitalised mid-sentence."""
    found = Counter()
    for line in text.splitlines():
        for i, m in enumerate(TECH_RE.finditer(line)):
            w = m.group(0).rstrip(".-/")
            prev = line[: m.start()].rstrip()
            mid = i > 0 and prev and prev[-1] not in ".:!?-"
            if re.search(r"[+#]|^\.\w|\w\.\w", w) or re.fullmatch(r"[A-Z]{2,}s?|[A-Z][a-z]+[A-Z]\w*", w) or (mid and w[0].isupper()):
                if w.lower() not in STOP and w.lower() not in ROLE_WORDS:
                    found[w.lower()] += 1
    return found


def cmd_keywords(a):
    posting = read_text(a.posting)
    resume = read_text(a.resume).lower()
    uni, bi = terms(posting)
    cand = [(t, n) for t, n in bi.items() if n >= 3]
    cand += [(t, uni[t] or n) for t, n in tools(posting).items()]
    cand += [(t, n) for t, n in uni.items() if n >= a.min_count]
    seen, rows = set(), []
    for t, n in sorted(cand, key=lambda x: (-x[1], x[0])):
        if t in seen:
            continue
        seen.add(t)
        hit = re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", resume) is not None
        rows.append({"term": t, "count": n, "in_resume": hit})
    rows = rows[: a.top]
    have = [r for r in rows if r["in_resume"]]
    cover = round(100 * len(have) / len(rows)) if rows else 0
    if a.json:
        print(json.dumps({"coverage": cover, "terms": rows}, indent=2))
        return
    print(f"coverage: {cover}% of {len(rows)} posting terms appear in the resume")
    print("missing (add only where true):")
    for r in rows:
        if not r["in_resume"]:
            print(f"  - {r['term']} (x{r['count']})")
    print("present: " + ", ".join(r["term"] for r in have))


# ---------- lint ----------

SECTIONS = {
    "experience": r"experience|employment|work history|professional history",
    "education": r"education|degrees?",
    "skills": r"skills|technologies|technical",
}


def lint_resume(path):
    p = Path(path)
    info = {"tables": 0, "columns": 1, "text_boxes": 0}
    if p.suffix.lower() == ".docx":
        text, info = docx_text(p)
    else:
        text = read_text(path)
        info["tables"] = len(re.findall(r"^\s*\|.*\|\s*$\n^\s*\|[\s:|-]+\|\s*$", text, flags=re.M))
    issues = []

    def add(level, msg):
        issues.append({"level": level, "msg": msg})

    if info["tables"]:
        add("error", f"{info['tables']} table(s): many ATS parsers read tables cell by cell and scramble the order")
    if info["columns"] > 1:
        add("error", f"{info['columns']}-column layout: parsers interleave the columns; use one column")
    if info["text_boxes"]:
        add("error", f"{info['text_boxes']} text box(es): parsers often skip text boxes")
    low = text.lower()
    heads = [l.strip("#*: ").lower() for l in text.splitlines() if l.strip() and len(l.strip()) < 40]
    for name, pat in SECTIONS.items():
        if not any(re.fullmatch(r"(?:" + pat + r")(?: .*)?", h) for h in heads):
            add("warn", f"no '{name}' heading found; use a plain standard heading")
    if not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
        add("error", "no email address")
    if not re.search(r"\+?\d[\d\s().-]{8,}\d", text):
        add("warn", "no phone number")
    words = len(re.findall(r"\w+", text))
    if words > 1100:
        add("warn", f"{words} words: about two pages is the usual ceiling")
    if words < 150:
        add("warn", f"only {words} words of text: is it a scan or an image? ATS cannot read images")
    if re.search(r"\b(I|me|my)\b", text):
        add("info", "first-person pronouns; resume bullets usually drop them")
    long = [l for l in text.splitlines() if l.strip().startswith(("-", "*", "•")) and len(l.split()) > 40]
    if long:
        add("info", f"{len(long)} bullet(s) over 40 words; split or cut")
    if re.search(r"[←-⇿☀-➿\U0001F300-\U0001FAFF]", text):
        add("warn", "symbols or emoji; some parsers drop or garble them")
    if not re.search(r"(19|20)\d\d", low):
        add("warn", "no years found; give dates for each role")
    return issues


def cmd_lint(a):
    issues = lint_resume(a.resume)
    if a.json:
        print(json.dumps(issues, indent=2))
    else:
        for i in issues:
            print(f"{i['level']}: {i['msg']}")
        if not issues:
            print("ok: no ATS problems found")
    sys.exit(1 if any(i["level"] == "error" for i in issues) else 0)


# ---------- render ----------

def _dates(x):
    s, e = x.get("startDate", ""), x.get("endDate", "") or ("Present" if x.get("startDate") else "")
    return f"{s[:7]} to {e[:7]}" if s else e


def render_md(r):
    b = r.get("basics", {})
    out = [f"# {b.get('name', 'Name')}"]
    if b.get("label"):
        out.append(b["label"])
    loc = b.get("location", {})
    contact = [b.get("email"), b.get("phone"), ", ".join(x for x in (loc.get("city"), loc.get("region")) if x), b.get("url")]
    contact += [p.get("url") for p in b.get("profiles", []) if p.get("url")]
    out.append(" | ".join(c for c in contact if c))
    if b.get("summary"):
        out += ["", "## Summary", b["summary"]]
    if r.get("skills"):
        out += ["", "## Skills"]
        for s in r["skills"]:
            out.append(f"- {s.get('name', '')}: {', '.join(s.get('keywords', []))}".rstrip(": "))
    if r.get("work"):
        out += ["", "## Experience"]
        for w in r["work"]:
            out += ["", f"### {w.get('position', '')}, {w.get('name', '')}", _dates(w)]
            if w.get("summary"):
                out.append(w["summary"])
            out += [f"- {h}" for h in w.get("highlights", [])]
    if r.get("projects"):
        out += ["", "## Projects"]
        for p in r["projects"]:
            out.append(f"- {p.get('name', '')}: {p.get('description', '')}".rstrip(": "))
    if r.get("education"):
        out += ["", "## Education"]
        for e in r["education"]:
            deg = " ".join(x for x in (e.get("studyType"), e.get("area")) if x)
            out.append(f"- {deg}, {e.get('institution', '')} {_dates(e)}".strip())
    for key, head in (("certificates", "Certificates"), ("languages", "Languages")):
        if r.get(key):
            out += ["", f"## {head}"]
            out += [f"- {x.get('name') or x.get('language', '')} {x.get('fluency', '') or x.get('issuer', '')}".strip() for x in r[key]]
    return "\n".join(out) + "\n"


def cmd_render(a):
    try:
        r = json.loads(Path(a.resume).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        die(f"{a.resume}: {e}")
    if not isinstance(r, dict) or "basics" not in r:
        die("not a JSON Resume (no 'basics')")
    md = render_md(r)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8", newline="\n")
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(md)


# ---------- tracker ----------

def tracker_path(a):
    return Path(a.file) if a.file else home() / "applications.json"


def load(path):
    if not path.exists():
        return {"applications": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path}: bad JSON: {e}")


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def today(a):
    return dt.date.fromisoformat(a.today) if getattr(a, "today", None) else dt.date.today()


def next_id(apps):
    return max([x["id"] for x in apps] or [0]) + 1


def follow_up(stage, day):
    n = FOLLOW_UP_DAYS.get(stage)
    return (day + dt.timedelta(days=n)).isoformat() if n else None


def find(apps, key):
    for x in apps:
        if str(x["id"]) == str(key):
            return x
    die(f"no application {key}")


def cmd_track(a):
    path = tracker_path(a)
    data = load(path)
    apps = data["applications"]
    day = today(a)
    if a.action == "add":
        if not a.company or not a.title:
            die("add needs --company and --title")
        if a.link and any(x.get("link") == a.link for x in apps):
            die(f"already tracked: {a.link}")
        stage = a.stage or "wishlist"
        x = {"id": next_id(apps), "company": a.company, "title": a.title, "link": a.link or "", "stage": stage,
             "created": day.isoformat(), "updated": day.isoformat(), "follow_up": follow_up(stage, day),
             "history": [{"date": day.isoformat(), "stage": stage, "note": a.note or ""}]}
        apps.append(x)
        save(path, data)
        print(f"added #{x['id']} {x['company']}: {x['title']} ({stage})")
    elif a.action == "move":
        if not a.id or not a.stage:
            die("move needs an id and --stage")
        x = find(apps, a.id)
        x["stage"], x["updated"] = a.stage, day.isoformat()
        x["follow_up"] = a.follow_up or follow_up(a.stage, day)
        x["history"].append({"date": day.isoformat(), "stage": a.stage, "note": a.note or ""})
        save(path, data)
        print(f"#{x['id']} {x['company']} -> {a.stage}" + (f", follow up {x['follow_up']}" if x["follow_up"] else ""))
    elif a.action == "list":
        rows = [x for x in apps if (not a.stage or x["stage"] == a.stage) and (a.all or x["stage"] not in CLOSED)]
        if a.json:
            print(json.dumps(rows, indent=2))
            return
        counts = Counter(x["stage"] for x in apps)
        print(" ".join(f"{s}:{counts[s]}" for s in STAGES if counts[s]) or "no applications")
        for x in sorted(rows, key=lambda x: (STAGES.index(x["stage"]), x["id"])):
            print(f"#{x['id']:<3} {x['stage']:<9} {x['company']}: {x['title']}" + (f"  (follow up {x['follow_up']})" if x.get("follow_up") else ""))
    elif a.action == "due":
        horizon = day + dt.timedelta(days=a.days)
        rows = [x for x in apps if x["stage"] not in CLOSED and x.get("follow_up") and dt.date.fromisoformat(x["follow_up"]) <= horizon]
        stale = [x for x in apps if x["stage"] == "wishlist" and (day - dt.date.fromisoformat(x["updated"])).days >= a.stale]
        if a.json:
            print(json.dumps({"due": rows, "stale_wishlist": stale}, indent=2))
            return
        for x in sorted(rows, key=lambda x: x["follow_up"]):
            late = (day - dt.date.fromisoformat(x["follow_up"])).days
            when = f"{late} day(s) late" if late > 0 else ("today" if late == 0 else x["follow_up"])
            print(f"follow up #{x['id']} {x['company']}: {x['title']} ({x['stage']}), {when}")
        for x in stale:
            print(f"stale wishlist #{x['id']} {x['company']}: {x['title']}, untouched {(day - dt.date.fromisoformat(x['updated'])).days} days: apply or archive")
        if not rows and not stale:
            print("nothing due")
    elif a.action == "import-leads":
        if not a.id:
            die("import-leads needs a leads markdown file")
        if not Path(a.id).exists():
            die(f"no such file: {a.id}")
        text = Path(a.id).read_text(encoding="utf-8", errors="replace")
        added = 0
        for m in re.finditer(r"^\*\*(.+?)\s+[—-]\s+(.+?)\*\*(.*)$", text, flags=re.M):
            company, title, rest = m.group(1).strip(), m.group(2).strip(), m.group(3)
            link = (re.search(r"https?://\S+", rest) or [""])[0]
            status = (re.search(r"status:\s*([\w-]+)", rest) or [None, ""])[1].lower()
            if status in ("rejected", "closed", "dead", "passed", "skip", "skipped"):
                continue
            if any((link and x.get("link") == link) or (x["company"], x["title"]) == (company, title) for x in apps):
                continue
            x = {"id": next_id(apps), "company": company, "title": title, "link": link, "stage": "wishlist",
                 "created": day.isoformat(), "updated": day.isoformat(), "follow_up": None,
                 "history": [{"date": day.isoformat(), "stage": "wishlist", "note": "imported from leads"}]}
            apps.append(x)
            added += 1
        save(path, data)
        print(f"imported {added} lead(s) into {path}")


# ---------- interview ----------

BEHAVIOURAL = [
    ("conflict", "Tell me about a time you disagreed with a teammate or manager on a technical decision. What happened?"),
    ("failure", "Tell me about a project that failed or slipped. What was your part, and what did you change afterwards?"),
    ("ownership", "Tell me about a time you took on a problem nobody owned. How did you get it done?"),
    ("influence", "Tell me about a time you changed how a team worked without being their manager. How?"),
    ("ambiguity", "Tell me about a time the requirements were unclear. How did you decide what to build?"),
    ("mentoring", "Tell me about someone you helped grow. What did you do, and what came of it?"),
    ("pressure", "Tell me about a production incident you handled. What did you do in the first hour?"),
    ("tradeoff", "Tell me about a time you chose speed over quality, or the other way round. Would you choose the same again?"),
]


def cmd_interview(a):
    role = a.role or "the role"
    qs = []
    posting_terms = []
    if a.posting:
        posting_terms = [t for t, _ in tools(read_text(a.posting)).most_common(a.tech)]
    qs += BEHAVIOURAL[: a.count]
    for t in posting_terms:
        slug = re.sub(r'[^a-z0-9]+', '-', t.replace('#', 'sharp').replace('+', 'plus').replace('.', 'dot')).strip('-')
        qs.append((f"tech-{slug}", f"The posting stresses {t}. Walk me through the hardest thing you have built or fixed with {t}. What did you do yourself?"))
    out = []
    for key, q in qs:
        out.append({
            "id": key[:60],
            "kind": "text",
            "title": f"Mock interview: {key.replace('-', ' ').replace('tech ', '', 1)}"[:80],
            "question": q,
            "background": f"Mock interview for {role}. Answer as you would out loud, in the STAR shape: Situation, Task, Action, Result. Two minutes spoken is about 250 words.",
            "why": "Your written answer gets scored for STAR shape, specifics and numbers, and comes back with a tighter version to rehearse aloud.",
            "guess": {"text": "Situation in one line, your own action in three or four specific steps, a measured result, and what you would do differently.",
                      "why": "The STAR outline, not an answer: the story has to be yours.", "confidence": "low"},
        })
    data = {"questions": out}
    if a.out:
        Path(a.out).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {len(out)} question(s) to {a.out}; add them with: ask.py add <set> {a.out}")
    else:
        print(json.dumps(data, indent=2))


def score_star(text):
    """Rough STAR rubric for an answer: which parts are present, specifics, length."""
    low = text.lower()
    parts = {
        "situation": bool(re.search(r"\b(when|at [A-Z]?\w+|we were|the team|our|in 20\d\d|last year)\b", low)),
        "task": bool(re.search(r"\b(needed to|had to|goal|my job|responsible|asked to|task)\b", low)),
        "action": len(re.findall(r"\bI (built|wrote|led|set up|changed|moved|proposed|talked|asked|fixed|added|cut|ran|designed|found|made|decided)\b", text, flags=re.I)) >= 2,
        "result": bool(re.search(r"\b(result|so that|which|cut|saved|reduced|increased|shipped|launched|down to|up to)\b", low)) and bool(re.search(r"\d", text)),
    }
    words = len(text.split())
    notes = [f"missing {k}" for k, v in parts.items() if not v]
    if words < 120:
        notes.append(f"short ({words} words): add the specifics")
    if words > 400:
        notes.append(f"long ({words} words): cut to about 250")
    if len(re.findall(r"\bwe\b", low)) > 2 * max(1, len(re.findall(r"\bi\b", low))):
        notes.append("mostly 'we': say what you did")
    return {"parts": parts, "words": words, "score": sum(parts.values()), "notes": notes}


def cmd_score(a):
    res = score_star(read_text(a.answer))
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"STAR {res['score']}/4, {res['words']} words")
        for n in res["notes"]:
            print(f"  - {n}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="cr.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keywords", help="posting terms present in or missing from a resume")
    k.add_argument("posting"); k.add_argument("resume")
    k.add_argument("--top", type=int, default=30); k.add_argument("--min-count", type=int, default=2)
    k.add_argument("--json", action="store_true"); k.set_defaults(fn=cmd_keywords)
    l = sub.add_parser("lint", help="ATS-safety checks on a resume (.md, .txt, .docx)")
    l.add_argument("resume"); l.add_argument("--json", action="store_true"); l.set_defaults(fn=cmd_lint)
    r = sub.add_parser("render", help="JSON Resume to single-column markdown")
    r.add_argument("resume"); r.add_argument("--out"); r.set_defaults(fn=cmd_render)
    t = sub.add_parser("track", help="application tracker")
    t.add_argument("action", choices=["add", "move", "list", "due", "import-leads"])
    t.add_argument("id", nargs="?", help="application id (move) or leads file (import-leads)")
    t.add_argument("--company"); t.add_argument("--title"); t.add_argument("--link")
    t.add_argument("--stage", choices=STAGES); t.add_argument("--note"); t.add_argument("--follow-up")
    t.add_argument("--days", type=int, default=0); t.add_argument("--stale", type=int, default=14)
    t.add_argument("--all", action="store_true"); t.add_argument("--json", action="store_true")
    t.add_argument("--file", help="tracker JSON (default CAREERWRIGHT_HOME/applications.json)")
    t.add_argument("--today", help=argparse.SUPPRESS); t.set_defaults(fn=cmd_track)
    i = sub.add_parser("interview", help="STAR mock-interview questions for askwright")
    i.add_argument("--role"); i.add_argument("--posting"); i.add_argument("--count", type=int, default=5, help="behavioural questions")
    i.add_argument("--tech", type=int, default=2, help="questions on the posting's named technologies")
    i.add_argument("--out"); i.set_defaults(fn=cmd_interview)
    s = sub.add_parser("score", help="rough STAR rubric for a written answer")
    s.add_argument("answer"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_score)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
