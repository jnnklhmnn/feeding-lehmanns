#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
MEAL_PLAN = ROOT / "meal-plan.md"
HISTORY = ROOT / "history.md"


def parse_markdown_table_lines(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        rows.append(cells)
    return rows


def load_meal_plan_entries() -> list[tuple[str, str]]:
    lines = MEAL_PLAN.read_text(encoding="utf-8").splitlines()
    rows = parse_markdown_table_lines(lines)
    entries: list[tuple[str, str]] = []

    for row in rows:
        if len(row) != 5:
            continue
        if row[0] == "Date" or row[0].startswith("---"):
            continue

        date, _day, dish, status, _notes = row
        if not date or not dish or dish == "TBD":
            continue
        if status not in {"planned", "cooked"}:
            continue

        entries.append((date, dish))

    return entries


def load_history_keys() -> set[tuple[str, str]]:
    lines = HISTORY.read_text(encoding="utf-8").splitlines()
    rows = parse_markdown_table_lines(lines)
    keys: set[tuple[str, str]] = set()

    for row in rows:
        if len(row) != 3:
            continue
        if row[0] == "Date" or row[0].startswith("---"):
            continue

        date, dish, _note = row
        if date and dish:
            keys.add((date, dish))

    return keys


def append_missing_entries() -> int:
    history_text = HISTORY.read_text(encoding="utf-8")
    if not history_text.endswith("\n"):
        history_text += "\n"

    existing = load_history_keys()
    additions: list[str] = []
    for date, dish in load_meal_plan_entries():
        key = (date, dish)
        if key in existing:
            continue
        additions.append(f"| {date} | {dish} | planned |\n")

    if not additions:
        return 0

    HISTORY.write_text(history_text + "".join(additions), encoding="utf-8")
    return len(additions)


if __name__ == "__main__":
    added = append_missing_entries()
    print(f"Added {added} history entr{'y' if added == 1 else 'ies'}.")
