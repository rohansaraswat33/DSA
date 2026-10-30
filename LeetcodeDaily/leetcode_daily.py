"""Fetch the LeetCode Daily Challenge for a date and the same date in every year back to 2020,
sorted easy to hard, and scaffold solution files with the problem statement plus starter code."""

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html import unescape

GRAPHQL_URL = "https://leetcode.com/graphql"
BASE_URL = "https://leetcode.com"
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "problems")
START_DATE = dt.date(2020, 4, 1)
MAX_WORKERS = 8
NETWORK_ERRORS = (urllib.error.URLError, RuntimeError, ValueError, TimeoutError)

# langSlug -> (file extension, block comment open/close, header prepended to the snippet)
LANGUAGES = {
    "cpp": (".cpp", "/*", "*/", "#include <bits/stdc++.h>\nusing namespace std;\n"),
    "java": (".java", "/*", "*/", ""),
    "javascript": (".js", "/*", "*/", ""),
    "python3": (".py", '"""', '"""', "from typing import List, Optional\n"),
}

MONTH_QUERY = """
query dailyCodingQuestionRecords($year: Int!, $month: Int!) {
  dailyCodingChallengeV2(year: $year, month: $month) {
    challenges {
      date
      link
      question {
        questionFrontendId
        title
        titleSlug
        difficulty
        acRate
        topicTags { name }
      }
    }
  }
}
"""

QUESTION_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    title
    titleSlug
    difficulty
    content
    hints
    topicTags { name }
    codeSnippets { langSlug code }
  }
}
"""

_month_cache = {}
_question_cache = {}


def graphql(query, variables, operation_name):
    payload = json.dumps(
        {"query": query, "variables": variables, "operationName": operation_name}
    ).encode("utf-8")

    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "leetcode-daily-cli/1.0",
            "Referer": BASE_URL,
        },
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))

    if body.get("errors"):
        raise RuntimeError(body["errors"][0].get("message", "GraphQL error"))
    return body.get("data") or {}


def fetch_month(year, month):
    key = (year, month)
    if key in _month_cache:
        return _month_cache[key]

    data = graphql(
        MONTH_QUERY, {"year": year, "month": month}, "dailyCodingQuestionRecords"
    )
    daily = data.get("dailyCodingChallengeV2") or {}
    challenges = {c["date"]: c for c in daily.get("challenges", [])}
    _month_cache[key] = challenges
    return challenges


def fetch_question(title_slug):
    if title_slug in _question_cache:
        return _question_cache[title_slug]

    question = graphql(QUESTION_QUERY, {"titleSlug": title_slug}, "questionData").get("question")
    _question_cache[title_slug] = question
    return question


def prefetch_questions(slugs):
    def warm(slug):
        try:
            fetch_question(slug)
        except NETWORK_ERRORS:
            pass  # the error resurfaces when the file is written

    if not slugs:
        return
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(slugs))) as pool:
        list(pool.map(warm, slugs))


def get_daily(day):
    challenges = fetch_month(day.year, day.month)
    return challenges.get(day.isoformat())


def load_daily(day):
    try:
        return day, get_daily(day), None
    except NETWORK_ERRORS as exc:
        return day, None, exc


def format_entry(day, challenge, verbose):
    header = f"{day.isoformat()} ({day.strftime('%A')})"
    if challenge is None:
        return f"{header}\n  No daily challenge found (LeetCode dailies start 2020-04-01).\n"

    q = challenge["question"]
    lines = [
        header,
        f"  {q['questionFrontendId']}. {q['title']}  [{q['difficulty']}]",
        f"  {BASE_URL}{challenge['link']}",
    ]
    if verbose:
        tags = ", ".join(t["name"] for t in q.get("topicTags", [])) or "-"
        lines.append(f"  Acceptance: {q['acRate']:.1f}%")
        lines.append(f"  Topics: {tags}")
    lines.append("")
    return "\n".join(lines)


def build_targets(base_day):
    targets = []
    for year in range(base_day.year, START_DATE.year - 1, -1):
        try:
            day = base_day.replace(year=year)
        except ValueError:
            # 29 Feb on a non-leap year falls back to 28 Feb.
            day = base_day.replace(year=year, day=28)
        if day >= START_DATE:
            targets.append(day)
    return targets


def sort_challenges(results):
    difficulty_order = {"Easy": 0, "Medium": 1, "Hard": 2}

    def sort_key(item):
        day, challenge = item
        if challenge is None:
            return (4, day)
        return (difficulty_order.get(challenge["question"].get("difficulty"), 3), day)

    results.sort(key=sort_key)
    return results


def html_to_text(html):
    if not html:
        return ""
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|pre|ul|ol|h[1-6]|table|tr)>", "\n", text)
    text = re.sub(r"(?i)<li>", "- ", text)
    text = re.sub(r"(?i)</li>", "\n", text)
    text = re.sub(r"(?i)<sup>", "^", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text).replace("\r\n", "\n").replace("\xa0", " ")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n[ \t]+- ", "\n- ", text)
    text = re.sub(r"(?m)^(- .*)\n\n+(?=- )", r"\1\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def pick_snippet(question, lang_slug):
    for snippet in question.get("codeSnippets") or []:
        if snippet["langSlug"] == lang_slug:
            return snippet["code"]
    return ""


def build_file_content(day, challenge, question, lang_slug):
    _, open_comment, close_comment, header = LANGUAGES[lang_slug]
    tags = ", ".join(t["name"] for t in question.get("topicTags", [])) or "-"

    block = [
        open_comment,
        f"{question['questionFrontendId']}. {question['title']}  [{question['difficulty']}]",
        f"Daily Challenge: {day.isoformat()}",
        f"{BASE_URL}{challenge['link']}",
        f"Topics: {tags}",
        "",
        html_to_text(question.get("content")),
    ]

    hints = question.get("hints") or []
    if hints:
        block.append("")
        block.append("Hints:")
        block.extend(f"{i}. {html_to_text(h)}" for i, h in enumerate(hints, 1))

    block.append(close_comment)

    parts = ["\n".join(block), ""]
    if header:
        parts.append(header)
    parts.append(pick_snippet(question, lang_slug) or "// No starter code available for this language.")
    parts.append("")
    return "\n".join(parts)


def folder_name(day):
    return day.strftime("%d-%b-%Y")


def slugify_filename(day, question):
    return f"{day.year}-{question['questionFrontendId']}-{question['titleSlug']}"


def solution_path(day, challenge, lang_slug, folder):
    name = slugify_filename(day, challenge["question"]) + LANGUAGES[lang_slug][0]
    return os.path.join(folder, name)


def create_solution_file(day, challenge, lang_slug, overwrite, folder):
    path = solution_path(day, challenge, lang_slug, folder)
    if os.path.exists(path) and not overwrite:
        return path, False

    question = fetch_question(challenge["question"]["titleSlug"])
    if question is None:
        raise RuntimeError("question details unavailable")

    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(build_file_content(day, challenge, question, lang_slug))
    return path, True


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="LeetCode daily challenge for a date and the same date in every year back to 2020."
    )
    parser.add_argument(
        "-d",
        "--date",
        help="Base date as YYYY-MM-DD (default: today).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show acceptance rate and topic tags.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of text.",
    )
    parser.add_argument(
        "--no-create",
        dest="create",
        action="store_false",
        help="Only list the problems, do not scaffold solution files.",
    )
    parser.add_argument(
        "-l",
        "--lang",
        default="cpp",
        choices=sorted(LANGUAGES),
        help="Language for the generated starter file (default: cpp).",
    )
    parser.add_argument(
        "-o",
        "--dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Root folder for generated files (default: LeetcodeDaily/problems).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing solution file instead of keeping your work.",
    )
    args = parser.parse_args(argv)

    if args.date:
        try:
            base_day = dt.date.fromisoformat(args.date)
        except ValueError:
            parser.error("--date must be in YYYY-MM-DD format")
    else:
        base_day = dt.date.today()

    if base_day < START_DATE:
        parser.error("--date must be on or after 2020-04-01")

    results = []
    targets = build_targets(base_day)
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(targets))) as pool:
        for day, challenge, error in pool.map(load_daily, targets):
            if error is not None:
                print(f"Failed to fetch {day.isoformat()}: {error}", file=sys.stderr)
            results.append((day, challenge))
    sort_challenges(results)

    if args.json:
        payload = [
            {"date": day.isoformat(), "challenge": challenge} for day, challenge in results
        ]
        print(json.dumps(payload, indent=2))
        return 0

    target_folder = os.path.join(args.dir, folder_name(base_day))

    if args.create:
        prefetch_questions(
            [
                challenge["question"]["titleSlug"]
                for day, challenge in results
                if challenge is not None
                and (
                    args.overwrite
                    or not os.path.exists(solution_path(day, challenge, args.lang, target_folder))
                )
            ]
        )

    print(f"LeetCode Daily Challenges on {base_day.strftime('%d %b')}, {START_DATE.year} to {base_day.year}")
    print("Sorted by difficulty: Easy, Medium, Hard")
    print("=" * 60)
    for day, challenge in results:
        print(format_entry(day, challenge, args.verbose), end="")
        if args.create and challenge is not None:
            try:
                path, created = create_solution_file(
                    day, challenge, args.lang, args.overwrite, target_folder
                )
                status = "created" if created else "exists"
                print(f"  File ({status}): {os.path.relpath(path, os.getcwd())}")
            except (urllib.error.URLError, RuntimeError, OSError, TimeoutError) as exc:
                print(f"  File creation failed: {exc}", file=sys.stderr)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
