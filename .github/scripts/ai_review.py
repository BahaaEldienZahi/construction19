"""AI review for Odoo pull requests.

Sends the PR diff to Claude, prints the issues it finds, and exits with
code 1 when it reports a critical issue so the GitHub check turns red.
"""

import json
import os
import subprocess
import sys

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
BASE_REF = os.environ.get("BASE_REF", "main")
PATHS = os.environ.get("REVIEW_PATHS", "nt_construction").split()
MAX_DIFF_CHARS = 150_000

SYSTEM_PROMPT = """You are a senior Odoo 19 developer reviewing a pull request
for a construction management module (tenders, BOQ, payment certificates,
variation orders, subcontracts).

Look for real problems only:
- Python syntax errors or code that will crash on module install/upgrade
- Broken XML views, wrong field names, missing records in __manifest__.py
- Missing access rights (ir.model.access.csv) for new models
- Wrong financial calculations (amounts, retention, taxes, progress %)
- Security issues (sudo misuse, SQL injection, missing record rules)
- Odoo 19 API mistakes

Do not report style or formatting preferences.

Respond ONLY with a JSON object, no markdown fences, in this exact shape:
{
  "verdict": "pass" or "fail",
  "summary": "one or two sentences",
  "issues": [
    {"severity": "critical" | "major" | "minor",
     "file": "path", "line": 0, "message": "what is wrong and how to fix it"}
  ]
}
Use "fail" only if at least one issue is critical."""


def get_diff() -> str:
    cmd = ["git", "diff", f"origin/{BASE_REF}...HEAD", "--", *PATHS]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def write_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def main() -> int:
    diff = get_diff()
    if not diff.strip():
        print("No changes in reviewed paths - skipping AI review.")
        return 0

    if len(diff) > MAX_DIFF_CHARS:
        print(f"Diff is large ({len(diff)} chars), reviewing the first {MAX_DIFF_CHARS}.")
        diff = diff[:MAX_DIFF_CHARS]

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Review this diff:\n\n{diff}"}],
    )
    raw = "".join(b.text for b in response.content if b.type == "text")
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        print("Could not parse AI response:\n", raw)
        return 1

    verdict = result.get("verdict", "fail")
    issues = result.get("issues", [])
    icon = {"critical": "🔴", "major": "🟠", "minor": "🟡"}

    lines = [
        f"## AI Review: {'✅ pass' if verdict == 'pass' else '❌ fail'}",
        "",
        result.get("summary", ""),
        "",
    ]
    for issue in issues:
        sev = issue.get("severity", "minor")
        lines.append(
            f"- {icon.get(sev, '⚪')} **{sev}** `{issue.get('file')}:{issue.get('line')}` "
            f"{issue.get('message')}"
        )
    report = "\n".join(lines)

    print(report)
    write_summary(report)
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
