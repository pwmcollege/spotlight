import random
from collections import deque
from functools import cache

import requests
from bs4 import BeautifulSoup
from bs4.filter import SoupStrainer


def catalog(path, key):
    response = requests.get(f"https://pwn.college/pwncollege_api/v1/{path}", timeout=30)
    response.raise_for_status()

    data = response.json()
    if not data["success"]:
        raise RuntimeError(data["error"])

    return data[key]


def is_course(dojo):
    if dojo["type"] == "course":
        return True

    response = requests.get(
        f"https://pwn.college/pwncollege_api/v1/dojos/{dojo['id']}/course", timeout=30
    )
    if (
        response.status_code == 404
        and response.json().get("error") == "This dojo is not a course"
    ):
        return False

    response.raise_for_status()
    if not response.json()["success"]:
        raise ValueError(f"Could not check course status for {dojo['id']}")

    return True


@cache
def modules(dojo):
    return {
        module["id"]: [challenge["id"] for challenge in module["challenges"]]
        for module in catalog(f"dojos/{dojo}/modules", "modules")
    }


@cache
def challenge_ids(dojo, module):
    # The module page exposes the numeric ID shared by every import of a challenge.
    page = requests.get(f"https://pwn.college/{dojo}/{module}/", timeout=30)
    if page.status_code in (401, 403, 404):
        return {}

    page.raise_for_status()
    html = BeautifulSoup(page.content, "html.parser", parse_only=SoupStrainer("input"))

    return {
        field.find_previous_sibling("input")["value"]: int(field["value"])
        for field in html.select('input[id="challenge"] + input[id="challenge-id"]')
        if field.get("value")
    }


def blocked_ids(rule):
    blocked = set()
    dojo = rule["dojo"]
    source = modules(dojo)
    module_ids = [rule["module"]] if "module" in rule else source

    for module in module_ids:
        slugs = [rule["challenge"]] if "challenge" in rule else source[module]
        if not slugs:
            continue

        ids = challenge_ids(dojo, module)
        for slug in slugs:
            if slug not in ids:
                raise ValueError(f"Unknown excluded challenge: {dojo}/{module}/{slug}")

            blocked.add(ids[slug])

    return blocked


def candidates(dojo):
    choices = [
        (module, slug)
        for module, challenges in modules(dojo).items()
        for slug in challenges
    ]
    random.shuffle(choices)

    for module, slug in choices:
        number = challenge_ids(dojo, module).get(slug)
        if number is not None:
            yield number, {"dojo": dojo, "module": module, "challenge": slug}


def draw(dojos, excluded, count, picks=None):
    sources = deque(candidates(dojo) for dojo in dojos)
    picks = dict(picks or {})
    slugs = {pick["import"]["challenge"] for pick in picks.values()}

    # Give each dojo a turn before taking a second pick from any dojo.
    while sources and len(picks) < count:
        source = sources.popleft()

        for number, ref in source:
            slug = ref["challenge"]
            if number in excluded or number in picks or slug in slugs:
                continue

            picks[number] = {"import": ref}
            slugs.add(slug)
            sources.append(source)
            break

    return picks


def load_pools(blacklist, destination, allow_course_dojos, course_dojos):
    blocked = {rule["dojo"] for rule in blacklist if "module" not in rule}
    dojos = catalog("dojos", "dojos")
    random.shuffle(dojos)

    community_dojos = []
    official_dojos = []
    for dojo in dojos:
        source = dojo["id"]
        kind = dojo["type"]
        if (
            source == destination
            or source in blocked
            or kind not in ("public", "welcome", "topic", "course")
        ):
            continue

        if not allow_course_dojos and (source in course_dojos or is_course(dojo)):
            continue

        if kind == "public" or (kind == "course" and not dojo["official"]):
            community_dojos.append(source)
        else:
            official_dojos.append(source)

    excluded = set().union(*(blocked_ids(rule) for rule in blacklist))
    return {"community": community_dojos, "official": official_dojos}, excluded


def draw_week(pools, excluded, counts):
    official = draw(pools["official"], excluded, counts["official"])
    community = draw(
        pools["community"], excluded | official.keys(), counts["community"]
    )

    if official and len(community) < counts["community"]:
        # A challenge shared by both pools may be needed to fill Community.
        community = draw(pools["community"], excluded, counts["community"], community)
        shared = official.keys() & community.keys()
        if shared:
            for number in shared:
                del official[number]

            official = draw(
                pools["official"],
                excluded | community.keys(),
                counts["official"],
                official,
            )

    return {"community": list(community.values()), "official": list(official.values())}
