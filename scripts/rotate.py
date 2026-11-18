import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from catalog import catalog, challenge_ids, draw_week, load_pools


def read_blacklist():
    config = yaml.safe_load(Path("blacklist.yml").read_text())
    rules = config["blacklist"]
    if not isinstance(rules, list):
        raise TypeError("blacklist must be a list")

    scopes = ({"dojo"}, {"dojo", "module"}, {"dojo", "module", "challenge"})
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) not in scopes:
            raise ValueError(f"Invalid blacklist entry: {rule}")

    courses = config.get("course_dojos", [])
    if not isinstance(courses, list) or not all(
        isinstance(dojo, str) for dojo in courses
    ):
        raise TypeError("course_dojos must be a list of dojo IDs")

    return rules, courses


def published_modules(destination):
    if destination:
        modules = catalog(f"dojos/{destination}/modules", "modules")

        return [
            module for module in modules if module["id"] in ("community", "official")
        ]

    modules = []
    for pool in ("community", "official"):
        path = Path(pool, "module.yml")
        if path.exists():
            module = yaml.safe_load(path.read_text())
            module["id"] = pool
            module["description"] = path.with_name("DESCRIPTION.md").read_text()

            modules.append(module)

    return modules


def rotate(destination=None, force=False):
    counts = {
        "community": int(os.environ["COMMUNITY_COUNT"]),
        "official": int(os.environ["OFFICIAL_COUNT"]),
    }
    if min(counts.values()) < 0 or not any(counts.values()):
        raise ValueError("Counts must be nonnegative and at least one must be positive")

    allow_course_dojos = os.environ["ALLOW_COURSE_DOJOS"].lower()
    if allow_course_dojos not in ("true", "false"):
        raise ValueError("ALLOW_COURSE_DOJOS must be true or false")

    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    today = (now - timedelta(hours=6, minutes=21)).date()
    sunday = today - timedelta(days=today.isoweekday() % 7)
    edition = f"Week of {sunday}"
    previous = published_modules(destination)

    if (
        not force
        and len(previous) == 2
        and all(
            (module.get("description") or "").strip() == edition for module in previous
        )
    ):
        print(f"{edition} already selected.")
        return

    path = Path("history.yml")
    history = set(yaml.safe_load(path.read_text()) or []) if path.exists() else set()
    published = set()

    for module in previous:
        if destination:
            ids = challenge_ids(destination, module["id"])
            published.update(ids[pick["id"]] for pick in module["challenges"])
        else:
            refs = (pick["import"] for pick in module["challenges"])
            published.update(
                challenge_ids(ref["dojo"], ref["module"])[ref["challenge"]]
                for ref in refs
            )

    blacklist, course_dojos = read_blacklist()
    pools, blocked = load_pools(
        blacklist, destination, allow_course_dojos == "true", course_dojos
    )

    history.update(published)
    picks = draw_week(pools, blocked | history, counts)
    if not any(picks.values()):
        if not history:
            raise ValueError("Both pools are empty and history is blank")

        # Prefer a new lineup across the cycle boundary when another pick exists.
        if published and published != history:
            picks = draw_week(pools, blocked | published, counts)

        if not any(picks.values()):
            picks = draw_week(pools, blocked, counts)

        if not any(picks.values()):
            raise ValueError("Both pools are empty even without history")

        history.clear()
        print("Both pools exhausted. Starting a new cycle.")

    for pool, challenges in picks.items():
        directory = Path(pool)
        directory.mkdir(exist_ok=True)
        directory.joinpath("DESCRIPTION.md").write_text(f"{edition}\n")
        directory.joinpath("module.yml").write_text(
            yaml.safe_dump(
                {"challenges": challenges}, sort_keys=False, allow_unicode=True
            )
        )

    path.write_text(yaml.safe_dump(sorted(history)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", nargs="?")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    os.chdir(Path(__file__).resolve().parents[1])
    rotate(args.destination, args.force)
