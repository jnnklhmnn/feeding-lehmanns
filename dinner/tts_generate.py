#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


DINNER_DIR = Path(__file__).resolve().parent
REPO_ROOT = DINNER_DIR.parent
DISHES_DIR = DINNER_DIR / "dishes"
MEAL_PLAN = DINNER_DIR / "meal-plan.md"
CONFIG_PATH = DINNER_DIR / "tts_config.json"
LEXICON_PATH = DINNER_DIR / "tts_lexicon.json"
GENERATED_DIR = DINNER_DIR / "generated_audio"
LOG_DIR = DINNER_DIR / "logs"

DAY_NAMES = {
    "de": {
        0: "Montag",
        1: "Dienstag",
        2: "Mittwoch",
        3: "Donnerstag",
        4: "Freitag",
        5: "Samstag",
        6: "Sonntag",
    },
    "en": {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday",
    },
}

MONTH_NAMES = {
    "de": {
        1: "Januar",
        2: "Februar",
        3: "März",
        4: "April",
        5: "Mai",
        6: "Juni",
        7: "Juli",
        8: "August",
        9: "September",
        10: "Oktober",
        11: "November",
        12: "Dezember",
    },
    "en": {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    },
}

UNIT_NAMES = {
    "de": {
        "piece": "Stück",
        "head": "Kopf",
        "can": "Dose",
        "clove": "Zehe",
        "bunch": "Bund",
        "box": "Packung",
        "jar": "Glas",
        "loaf": "Laib",
    },
    "en": {
        "piece": "piece",
        "head": "head",
        "can": "can",
        "clove": "clove",
        "bunch": "bunch",
        "box": "box",
        "jar": "jar",
        "loaf": "loaf",
    },
}


@dataclass
class PlanEntry:
    date: str
    day: str
    dish: str
    status: str
    notes: str


def parse_markdown_table_lines(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
    return rows


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_lexicon() -> dict[str, Any]:
    return json.loads(LEXICON_PATH.read_text(encoding="utf-8"))


def resolve_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if path.is_absolute():
        return path
    return DINNER_DIR / path


def localized_day_name(language: str, day_value: date) -> str:
    return DAY_NAMES[language][day_value.weekday()]


def format_date(language: str, date_str: str) -> str:
    day_value = date.fromisoformat(date_str)
    if language == "de":
        return f"{localized_day_name(language, day_value)}, {day_value.day}. {MONTH_NAMES[language][day_value.month]}"
    return f"{localized_day_name(language, day_value)}, {MONTH_NAMES[language][day_value.month]} {day_value.day}"


def list_plan_entries() -> list[PlanEntry]:
    rows = parse_markdown_table_lines(MEAL_PLAN.read_text(encoding="utf-8").splitlines())
    entries: list[PlanEntry] = []
    for row in rows:
        if len(row) != 5:
            continue
        if row[0] == "Date" or row[0].startswith("---"):
            continue
        entries.append(PlanEntry(*row))
    return entries


def normalize_filename(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{slug}.json"


def dish_path_from_entry(entry: PlanEntry) -> Path:
    note_match = re.search(r"([\w-]+\.json)", entry.notes)
    if note_match:
        path = DISHES_DIR / note_match.group(1)
        if path.exists():
            return path

    candidate = DISHES_DIR / normalize_filename(entry.dish)
    if candidate.exists():
        return candidate

    raise FileNotFoundError(f"Could not resolve dish file for meal plan entry '{entry.dish}'")


def load_dish(path_or_name: str) -> dict[str, Any]:
    candidate = Path(path_or_name)
    if candidate.suffix == ".json":
        path = candidate if candidate.is_absolute() else (DINNER_DIR / candidate)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))

    normalized = normalize_filename(path_or_name)
    by_file = DISHES_DIR / normalized
    if by_file.exists():
        return json.loads(by_file.read_text(encoding="utf-8"))

    for dish_file in sorted(DISHES_DIR.glob("*.json")):
        if dish_file.name == "_template.json":
            continue
        data = json.loads(dish_file.read_text(encoding="utf-8"))
        if data.get("title", "").lower() == path_or_name.lower():
            return data

    raise FileNotFoundError(f"Could not find dish '{path_or_name}'")


def localize_dish_title(title: str, language: str, lexicon: dict[str, Any]) -> str:
    return lexicon.get("dish_titles", {}).get(language, {}).get(title, title)


def localize_ingredient_name(name: str, language: str, lexicon: dict[str, Any]) -> str:
    return lexicon.get("ingredient_names", {}).get(language, {}).get(name, name)


def localize_unit(unit: str, language: str) -> str:
    return UNIT_NAMES.get(language, {}).get(unit, unit)


def amount_text(item: dict[str, Any], language: str) -> str:
    amount = item.get("amount")
    if isinstance(amount, float) and amount.is_integer():
        amount = int(amount)
    unit = item.get("unit", "")
    localized_unit = localize_unit(unit, language)
    return f"{amount} {localized_unit}".strip()


def ingredient_line(item: dict[str, Any], language: str, lexicon: dict[str, Any]) -> str:
    name = localize_ingredient_name(item["name"], language, lexicon)
    amount = amount_text(item, language)
    knuspr = item.get("knuspr", {})

    if language == "de":
        if knuspr.get("ask_user"):
            options = [option["label"] for option in knuspr.get("options", [])]
            options_text = " oder ".join(options) if options else name
            return f"{amount} {options_text}, Auswahl noch offen"
        return f"{amount} {name}".strip()

    if knuspr.get("ask_user"):
        options = [option["label"] for option in knuspr.get("options", [])]
        options_text = " or ".join(options) if options else name
        return f"{amount} {options_text}, choice still open"

    return f"{amount} {name}".strip()


def aggregate_shopping_list(entries: list[PlanEntry]) -> list[dict[str, Any]]:
    aggregated: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for entry in entries:
        if entry.status not in {"planned", "cooked"} or entry.dish == "TBD":
            continue
        dish = json.loads(dish_path_from_entry(entry).read_text(encoding="utf-8"))
        for section in ("ingredients",):
            for item in dish.get(section, []):
                item_id = item["id"]
                if item_id in aggregated:
                    aggregated[item_id]["amount"] += item.get("amount", 0)
                else:
                    aggregated[item_id] = json.loads(json.dumps(item))
    return list(aggregated.values())


def build_meal_plan_text(language: str, lexicon: dict[str, Any]) -> str:
    entries = [entry for entry in list_plan_entries() if entry.status in {"planned", "cooked"} and entry.dish != "TBD"]
    if language == "de":
        intro = "Hier ist der aktuelle Essensplan für Feeding Lehmann."
    else:
        intro = "Here is the current Feeding Lehmann meal plan."

    parts = [intro]
    for entry in entries:
        dish_name = localize_dish_title(entry.dish, language, lexicon)
        if language == "de":
            parts.append(f"{format_date(language, entry.date)}: {dish_name}.")
        else:
            parts.append(f"{format_date(language, entry.date)}: {dish_name}.")
    return " ".join(parts)


def build_shopping_list_text(language: str, lexicon: dict[str, Any]) -> str:
    entries = list_plan_entries()
    items = aggregate_shopping_list(entries)

    if language == "de":
        parts = ["Hier ist die aktuelle Einkaufsliste für Feeding Lehmann."]
        for item in items:
            parts.append(f"{ingredient_line(item, language, lexicon)}.")
        return " ".join(parts)

    parts = ["Here is the current Feeding Lehmann shopping list."]
    for item in items:
        parts.append(f"{ingredient_line(item, language, lexicon)}.")
    return " ".join(parts)


def build_dish_text(dish: dict[str, Any], language: str, lexicon: dict[str, Any], include_optional: bool) -> str:
    title = localize_dish_title(dish["title"], language, lexicon)
    ingredients = [ingredient_line(item, language, lexicon) for item in dish.get("ingredients", [])]
    optional_ingredients = [ingredient_line(item, language, lexicon) for item in dish.get("optional_ingredients", [])]

    localized_note = lexicon.get("dish_notes", {}).get(language, {}).get(dish["title"], dish.get("notes", ""))

    if language == "de":
        parts = [
            f"Gericht: {title}.",
            f"Portionen: {dish.get('servings', 'unbekannt')}.",
            f"Zeitaufwand: {dish.get('time_rating', 'unbekannt')} von 5.",
            "Zutaten: " + ", ".join(ingredients) + ".",
        ]
        if include_optional and optional_ingredients:
            parts.append("Optionale Zutaten: " + ", ".join(optional_ingredients) + ".")
        if localized_note:
            parts.append("Hinweis: " + localized_note)
        return " ".join(parts)

    parts = [
        f"Dish: {title}.",
        f"Servings: {dish.get('servings', 'unknown')}.",
        f"Time effort: {dish.get('time_rating', 'unknown')} out of 5.",
        "Ingredients: " + ", ".join(ingredients) + ".",
    ]
    if include_optional and optional_ingredients:
        parts.append("Optional ingredients: " + ", ".join(optional_ingredients) + ".")
    if localized_note:
        parts.append("Note: " + localized_note)
    return " ".join(parts)


def build_text(args: argparse.Namespace, lexicon: dict[str, Any]) -> str:
    if args.command == "meal-plan":
        return build_meal_plan_text(args.language, lexicon)
    if args.command == "shopping-list":
        return build_shopping_list_text(args.language, lexicon)
    if args.command == "dish":
        dish = load_dish(args.dish)
        return build_dish_text(dish, args.language, lexicon, args.include_optional)
    if args.command == "text":
        return args.text
    raise ValueError(f"Unsupported command: {args.command}")


def default_output_path(command: str, language: str, format_name: str) -> Path:
    suffix = "wav" if format_name == "wav" else "ogg"
    return GENERATED_DIR / f"{command}-{language}.{suffix}"


def ensure_voice_available(python_bin: Path, voice_dir: Path, voice_name: str) -> None:
    model_path = voice_dir / f"{voice_name}.onnx"
    config_path = voice_dir / f"{voice_name}.onnx.json"
    if model_path.exists() and config_path.exists():
        return

    raise FileNotFoundError(
        f"Voice '{voice_name}' is missing in '{voice_dir}'. Download it with: "
        f"{python_bin} -m piper.download_voices --download-dir {voice_dir} {voice_name}"
    )


def synthesize(text: str, language: str, output_path: Path, args: argparse.Namespace) -> None:
    config = load_config()
    python_bin = resolve_path(os.environ.get("FEEDING_LEHMANNS_PIPER_PYTHON", config["python_bin"]))
    voice_dir = resolve_path(os.environ.get("FEEDING_LEHMANNS_PIPER_VOICE_DIR", config["voice_dir"]))
    voice_name = args.voice or config["voices"][language]

    ensure_voice_available(python_bin, voice_dir, voice_name)

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        temp_wav_path = Path(temp_wav.name)

    try:
        cmd = [
            str(python_bin),
            "-m",
            "piper",
            "-m",
            voice_name,
            "--data-dir",
            str(voice_dir),
            "-f",
            str(temp_wav_path),
            "--",
            text,
        ]
        subprocess.run(cmd, check=True, text=True, capture_output=True)

        if output_path.suffix.lower() == ".wav":
            output_path.parent.mkdir(parents=True, exist_ok=True)
            temp_wav_path.replace(output_path)
            return

        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(temp_wav_path),
            "-c:a",
            "libopus",
            "-b:a",
            "32k",
            str(output_path),
        ]
        subprocess.run(ffmpeg_cmd, check=True, text=True, capture_output=True)
    finally:
        if temp_wav_path.exists():
            temp_wav_path.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Feeding Lehmann audio with Piper.")
    parser.add_argument("--language", choices=["de", "en"], default="de")
    parser.add_argument("--voice", help="Override configured Piper voice.")
    parser.add_argument("--output", help="Output file path. Defaults to dinner/generated_audio/<command>-<lang>.<ext>.")
    parser.add_argument("--format", choices=["ogg", "wav"], default="ogg")
    parser.add_argument("--print-text", action="store_true", help="Print generated text before synthesis.")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("meal-plan", help="Speak the current meal plan.")
    subparsers.add_parser("shopping-list", help="Speak the shopping list aggregated from the current meal plan.")

    dish_parser = subparsers.add_parser("dish", help="Speak a dish summary from a dish file.")
    dish_parser.add_argument("dish", help="Dish filename slug, path, or exact title.")
    dish_parser.add_argument("--include-optional", action="store_true", help="Include optional ingredients.")

    text_parser = subparsers.add_parser("text", help="Speak arbitrary text.")
    text_parser.add_argument("text", help="Text to synthesize.")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    lexicon = load_lexicon()
    text = build_text(args, lexicon)

    if args.print_text:
        print(text)

    output_path = Path(args.output) if args.output else default_output_path(args.command, args.language, args.format)
    synthesize(text, args.language, output_path, args)
    print(output_path)


if __name__ == "__main__":
    main()
