# Research

## 2026-11-25: first pass
- Prior art: JSON Resume (MIT schema), RenderCV (MIT, local renderer), Reactive Resume (MIT web app), Resume-Matcher (Apache-2.0, keyword and similarity scoring). careerwright reads JSON Resume and keeps its own scoring stdlib-only; no code copied.
- MCP servers exist (JobApply-MCP-Server, resume-mcp, jobContextMCP and others); none bundled. Check again before building one.
- ATS parsing: single-column plain text parses reliably; tables, columns and text boxes get interleaved or skipped. Text PDFs and DOCX parse alike; scanned PDFs fail.
- Cover letters: vendor-run hiring-manager surveys say tailored letters help and generic ones hurt. Soft evidence.
- Structured (STAR) behavioural interviews predict performance better than unstructured ones (Schmidt and Hunter 1998; Levashina et al. 2014). Spoken rehearsal beats silent review.
- Tracker stages common across tools (Huntr, Teal, Simplify): wishlist, applied, interview stages, offer, rejected or archived, with follow-up dates.
