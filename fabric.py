"""Inspect FABRIC and generate a report for manual KB selection."""
import argparse
from collections import Counter
from pathlib import Path
import re

from datasets import load_dataset

QUOTAS = {
    "income_tax": 20, "banking_rbi": 18, "mutual_funds": 18,
    "stock_market": 16, "insurance": 14, "retirement": 14,
    "sebi_regulations": 12, "financial_literacy": 4, "employment_benefits": 4,
}
REQUIRED = ("id", "category", "difficulty", "question_en", "answer", "source")


def normalize(value):
    return " ".join(str(value or "").split()).casefold()


def build_report(records):
    ids = Counter(normalize(r.get("id")) for r in records)
    questions = Counter(normalize(r.get("question_en")) for r in records)
    answers = Counter(normalize(r.get("answer")) for r in records)
    reviewed = []
    for row in records:
        issues = [f"missing/blank {f}" for f in REQUIRED if not normalize(row.get(f))]
        if ids[normalize(row.get("id"))] > 1:
            issues.append("duplicate normalized ID")
        if questions[normalize(row.get("question_en"))] > 1:
            issues.append("duplicate normalized English question")
        cues = ["manually verify claims and source references"]
        answer = normalize(row.get("answer"))
        if answer and answers[answer] > 1:
            cues.append("repeated answer: check knowledge overlap")
        if re.search(r"\b(currently|latest|recent|today|as of|fy|ay)\b|\b20\d{2}\b|%|₹|\brs\.?\s*\d", answer):
            cues.append("dates, amounts, rates or time wording: check currency and scope")
        category = row.get("category")
        if category == "guardrails":
            role = "Safety review pool; keep outside Chroma"
        elif category not in QUOTAS:
            role = "Outside initial topic scope; retain for later review"
        elif issues:
            role = "Blocked candidate; resolve structural issues"
        else:
            role = "KB candidate; pending manual review"
        reviewed.append((row, issues, cues, role))

    lines = ["# FABRIC candidate review", "",
             "Dataset: `agenticclass/fabric`, split: `train`.",
             f"Records inspected: {len(records)}. Proposed KB size: {sum(QUOTAS.values())}.", "",
             "No records are selected or approved by this report. Flags are review cues, not financial fact checks.",
             "Source descriptions are dataset references, not downloaded or verified supporting documents.",
             "Duplicate checks ignore case and repeated whitespace. Semantic overlap still needs manual review.", "",
             "## Proposed allocation", "",
             "| Category | Available | Structurally eligible | Target | Shortfall |",
             "|---|---:|---:|---:|---:|"]
    for category, target in QUOTAS.items():
        available = sum(r.get("category") == category for r in records)
        eligible = sum(r.get("category") == category and not issues for r, issues, _, _ in reviewed)
        lines.append(f"| {category} | {available} | {eligible} | {target} | {max(0, target - eligible)} |")
    lines += ["", "Adjust quotas if content review rejects candidates; do not fill quotas with unsuitable answers.",
              "Preserve a reasonable difficulty mix after reviewing the available records.", "",
              "## Structural checks", "",
              f"Records with structural issues: {sum(bool(x[1]) for x in reviewed)}", ""]
    for field in REQUIRED:
        nulls = sum(r.get(field) is None for r in records)
        blanks = sum(r.get(field) is not None and not normalize(r.get(field)) for r in records)
        lines.append(f"- {field}: {nulls} null/missing, {blanks} blank")
    lines += ["", "## Review process", "",
              "Review question, answer and references for ambiguity, overlap, and time-sensitive claims.",
              "Verify material claims against primary sources before approval. Fill Decision and Reason below.",
              "Inspect guardrail expectations separately before using them for safety testing.",
              "Create separate paraphrased evaluation questions supported by approved KB records, plus unanswerable cases.", ""]
    categories = list(QUOTAS) + sorted({r["category"] for r in records} - set(QUOTAS))
    for category in categories:
        members = [x for x in reviewed if x[0]["category"] == category]
        counts = dict(sorted(Counter(x[0]["difficulty"] for x in members).items()))
        lines += [f"## Category: {category}", "", f"Difficulty counts: {counts}", ""]
        for row, issues, cues, role in sorted(members, key=lambda x: str(x[0].get("id", ""))):
            lines += [f"### {row.get('id', '(missing)')}", "", f"**Role:** {role}",
                      f"**Subcategory:** {row.get('subcategory', '')} | **Difficulty:** {row.get('difficulty', '')}", "",
                      f"**Question:** {row.get('question_en', '')}", "",
                      f"**Answer:** {row.get('answer', '')}", "",
                      f"**Source:** {row.get('source', '')}", "",
                      f"**Structural issues:** {'; '.join(issues) or 'none detected'}",
                      f"**Review cues:** {'; '.join(cues)}", "",
                      "**Decision:** pending", "", "**Reason / verification notes:**", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("reports/fabric_candidates.md"))
    parser.add_argument("--overwrite", action="store_true", help="Replace report, including any manual review notes.")
    args = parser.parse_args()
    if args.report.exists() and not args.overwrite:
        parser.error("Report already exists. Use another --report path or --overwrite.")
    dataset = load_dataset("agenticclass/fabric")
    data = dataset["train"]
    print("Available splits:\n", dataset)
    print("Dataset columns:", data.column_names)
    missing = set(REQUIRED) - set(data.column_names)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    records = list(data)
    print("Total records:", len(records))
    print("Category distribution:", dict(Counter(r["category"] for r in records)))
    print("Difficulty distribution:", dict(Counter(r["difficulty"] for r in records)))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w" if args.overwrite else "x", encoding="utf-8") as handle:
        handle.write(build_report(records))
    print(f"Report written: {args.report.resolve()}")
    print("Final KB selection has not been made. Review candidates before export.")


if __name__ == "__main__":
    main()
