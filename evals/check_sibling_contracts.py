"""Compare shared contracts without installing either collection or invoking a model."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_SKILLS = ("current-docs",)
SHARED_REFERENCES = ("evidence-driven-testing/references/data-workflows.md",)


def skill_root(repo):
    plugin = repo / "plugins/ronny-codex-skills/skills"
    return plugin if plugin.is_dir() else repo


def compare(first, second):
    problems = []
    a, b = (json.loads((root / "evals/outcome_contracts.json").read_text()) for root in (first, second))
    if a != b:
        problems.append("outcome prompts, deliverables or grading contract names differ")
    for skill in SHARED_SKILLS:
        if (skill_root(first) / skill / "SKILL.md").read_bytes() != (skill_root(second) / skill / "SKILL.md").read_bytes():
            problems.append(f"shared guidance differs: {skill}")
    for reference in SHARED_REFERENCES:
        if (skill_root(first) / reference).read_bytes() != (skill_root(second) / reference).read_bytes():
            problems.append(f"shared guidance differs: {reference}")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sibling", type=Path, help="Path to the other source checkout")
    args = parser.parse_args()
    try:
        problems = compare(ROOT, args.sibling.resolve())
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if problems:
        for problem in problems:
            print(problem)
        return 1
    print("Shared outcome contracts, the shared current-docs skill and data guidance match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
