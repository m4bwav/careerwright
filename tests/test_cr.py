import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CR = ROOT / "scripts" / "cr.py"
FX = Path(__file__).parent / "fixtures"


def run(*args, env=None):
    return subprocess.run([sys.executable, str(CR), *map(str, args)], capture_output=True, text=True, encoding="utf-8", env=env)


def make_docx(path, body):
    xml = f'<?xml version="1.0"?><w:document xmlns:w="w"><w:body>{body}</w:body></w:document>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", xml)


def para(t):
    return f"<w:p><w:r><w:t>{t}</w:t></w:r></w:p>"


def test_keywords_finds_missing_terms():
    r = run("keywords", FX / "posting.txt", FX / "resume.md", "--json")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    missing = {t["term"] for t in d["terms"] if not t["in_resume"]}
    present = {t["term"] for t in d["terms"] if t["in_resume"]}
    assert {"kafka", "kubernetes"} <= missing
    assert {"c#", ".net", "postgresql"} <= present
    assert 0 < d["coverage"] < 100


def test_lint_clean_markdown():
    r = run("lint", FX / "resume.md")
    assert r.returncode == 0, r.stdout
    assert "error" not in r.stdout


def test_lint_flags_table_and_columns_in_docx(tmp_path):
    p = tmp_path / "r.docx"
    body = para("Alex Example") + para("alex@example.com") + "<w:tbl><w:tr><w:tc>" + para("Skills") + "</w:tc></w:tr></w:tbl>"
    body += '<w:sectPr><w:cols w:space="720" w:num="2"/></w:sectPr>'
    make_docx(p, body)
    r = run("lint", p, "--json")
    assert r.returncode == 1
    msgs = " ".join(i["msg"] for i in json.loads(r.stdout))
    assert "table" in msgs and "2-column" in msgs and "experience" in msgs


def test_lint_flags_missing_email(tmp_path):
    p = tmp_path / "r.md"
    p.write_text((FX / "resume.md").read_text(encoding="utf-8").replace("alex@example.com", "alex at example"), encoding="utf-8")
    r = run("lint", p)
    assert r.returncode == 1 and "no email" in r.stdout


def test_render_json_resume(tmp_path):
    out = tmp_path / "r.md"
    r = run("render", FX / "resume.json", "--out", out)
    assert r.returncode == 0, r.stderr
    md = out.read_text(encoding="utf-8")
    assert md.startswith("# Alex Example")
    assert "## Experience" in md and "2019-03 to Present" in md and "|" in md.splitlines()[2]
    assert "BS Computer Science, State University 2011-09 to 2015-05" in md


def test_render_rejects_non_resume(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    assert run("render", p).returncode == 2


def test_tracker_flow(tmp_path):
    f = tmp_path / "apps.json"
    assert run("track", "add", "--company", "Acme", "--title", "Engineer", "--link", "https://e/1", "--file", f, "--today", "2026-01-01").returncode == 0
    assert run("track", "add", "--company", "Acme", "--title", "Engineer", "--link", "https://e/1", "--file", f).returncode == 2
    r = run("track", "move", "1", "--stage", "applied", "--note", "sent", "--file", f, "--today", "2026-01-02")
    assert "follow up 2026-01-09" in r.stdout
    assert "nothing due" in run("track", "due", "--file", f, "--today", "2026-01-05").stdout
    assert "2 day(s) late" in run("track", "due", "--file", f, "--today", "2026-01-11").stdout
    run("track", "move", "1", "--stage", "rejected", "--file", f, "--today", "2026-01-12")
    assert "#1" not in run("track", "list", "--file", f).stdout
    assert "#1" in run("track", "list", "--all", "--file", f).stdout
    d = json.loads(f.read_text(encoding="utf-8"))
    assert [h["stage"] for h in d["applications"][0]["history"]] == ["wishlist", "applied", "rejected"]


def test_import_leads_skips_rejected_and_duplicates(tmp_path):
    f = tmp_path / "apps.json"
    r = run("track", "import-leads", FX / "leads.md", "--file", f)
    assert "imported 2" in r.stdout
    assert "imported 0" in run("track", "import-leads", FX / "leads.md", "--file", f).stdout
    d = json.loads(f.read_text(encoding="utf-8"))
    assert {a["company"] for a in d["applications"]} == {"Acme Corp", "Initech"}
    assert d["applications"][0]["link"] == "https://example.com/jobs/1"


def test_stale_wishlist(tmp_path):
    f = tmp_path / "apps.json"
    run("track", "add", "--company", "A", "--title", "T", "--file", f, "--today", "2026-01-01")
    assert "stale wishlist #1" in run("track", "due", "--file", f, "--today", "2026-01-20").stdout


def test_interview_questions_are_askwright_text(tmp_path):
    out = tmp_path / "q.json"
    r = run("interview", "--role", "Backend Engineer", "--posting", FX / "posting.txt", "--count", "3", "--out", out)
    assert r.returncode == 0, r.stderr
    qs = json.loads(out.read_text(encoding="utf-8"))["questions"]
    assert len(qs) >= 4
    for q in qs:
        assert q["kind"] == "text" and q["question"].endswith("?") and q["background"] and q["why"]
        assert q["guess"]["confidence"] == "low" and len(q["title"]) <= 80
    assert len({q["id"] for q in qs}) == len(qs)


def test_score_star():
    r = run("score", FX / "answer.txt", "--json")
    d = json.loads(r.stdout)
    assert d["score"] == 4, d


def test_score_weak_answer(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("We worked hard and we shipped it.", encoding="utf-8")
    d = json.loads(run("score", p, "--json").stdout)
    assert d["score"] < 3 and any("short" in n for n in d["notes"])
