# engine.py
# GridLock recommendation agent.
#
# Reads the deterministic results from /opportunities (plus project details
# from /projects) and explains them in plain language for the front end.
#
# Rules (agreed with the data team):
# - It NEVER creates pairs, distances, dates, feasibility, or savings.
# - It only explains what /opportunities already returned.
# - Need Date is not an in-service date; a missing construction_end means
#   the timeline is unknown.
# - Pairs without timeline overlap are "future watch", not active coordination.
# - If there are no valid pairs, it says so and lists the missing evidence.
#
# Usage:
#   python recommendations/engine.py                 -> uses local repo files
#   python recommendations/engine.py --api URL       -> uses the live API
#   python recommendations/engine.py --self-test     -> synthetic format test

import json
import sys
import urllib.request

PROJECTS_FILE = "data/master_projects.json"

UTILITY_NAMES = {
    "dominion_sc": "Dominion Energy South Carolina (DESC)",
    "georgia_power": "Georgia Power (GPC)",
}

CATEGORIES = {
    "overlap": {
        "label": "Coordination to investigate",
        "priority": 1,
        "next_step": (
            "Confirm both construction windows with each utility's planning "
            "team, then review whether staging, access, or outage timing "
            "could be coordinated. Treat this as an investigation, not a "
            "confirmed plan."
        ),
    },
    "unknown": {
        "label": "Nearby - timing unconfirmed",
        "priority": 2,
        "next_step": (
            "Obtain source-backed construction start and end dates for both "
            "projects. Until then, proximity is the only confirmed signal."
        ),
    },
    "no_overlap": {
        "label": "Future watch",
        "priority": 3,
        "next_step": (
            "Keep this pair on a watch list and re-check if either schedule "
            "changes. It is not an active coordination opportunity."
        ),
    },
}


# ---------------------------------------------------------------- loading

def load_json_from_file(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def load_json_from_api(url):
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def index_projects(projects_payload):
    projects_by_id = {}
    for project in projects_payload["projects"]:
        projects_by_id[project["project_id"]] = project
    return projects_by_id


def load_data(api_base=None):
    """Returns (projects_by_id, opportunities)."""
    if api_base:
        api_base = api_base.rstrip("/")
        projects = load_json_from_api(api_base + "/projects")
        opportunities = load_json_from_api(api_base + "/opportunities")
        return index_projects(projects), opportunities["opportunities"]

    # Offline mode: the repo has no saved /opportunities file, and the current
    # live response is empty, so offline mode uses an empty list.
    projects = load_json_from_file(PROJECTS_FILE)
    return index_projects(projects), []


# ---------------------------------------------------------------- helpers

def classify(opportunity):
    status = opportunity["timeline_status"]
    if status not in CATEGORIES:
        raise ValueError(f"Unexpected timeline_status: {status}")
    return CATEGORIES[status]


def utility_name(project):
    return UTILITY_NAMES.get(project["utility_id"], project["utility_id"])


def describe_schedule(project):
    """Describes dates exactly as stored. Never converts one date type into another."""
    parts = []
    if project.get("construction_start"):
        parts.append(f"construction start {project['construction_start']}")
    if project.get("construction_end"):
        parts.append(f"construction end {project['construction_end']}")
    if project.get("in_service_date"):
        parts.append(f"in-service {project['in_service_date']}")
    if parts:
        return ", ".join(parts)
    if project.get("schedule_text"):
        return f"source wording: \"{project['schedule_text']}\""
    return "no schedule in the source"


# ---------------------------------------------------------------- explanations

def why_flagged(opportunity, project_a, project_b):
    distance = round(opportunity["distance_miles"], 2)
    status = opportunity["timeline_status"]

    text = (
        f"{project_a['project_name']} ({utility_name(project_a)}) and "
        f"{project_b['project_name']} ({utility_name(project_b)}) have "
        f"representative points {distance} miles apart, within the 25-mile "
        f"threshold."
    )
    if status == "overlap":
        text += " Their stated construction windows overlap."
    elif status == "no_overlap":
        text += " Their stated construction windows do not overlap."
    else:
        text += " Whether their construction windows overlap is unknown."
    return text


def uncertainties(opportunity, project_a, project_b):
    items = [
        "Distance is measured between representative points, not between "
        "full transmission routes."
    ]

    if opportunity["location_uncertain"]:
        items.append("At least one location is approximate.")

    for project in (project_a, project_b):
        name = project["project_name"]
        if project.get("location_quality") == "approximate":
            method = project.get("location_method") or "method not stated"
            items.append(f"{name}: approximate location ({method}).")
        if not project.get("construction_end"):
            items.append(f"{name}: no source-backed construction end date.")
        if project.get("review_status") != "validated":
            items.append(f"{name}: record still needs review.")

    items.append(
        "Resource sharing, outage impact, and savings are not established "
        "by this data."
    )
    return items


def evidence(project_a, project_b):
    items = []
    for project in (project_a, project_b):
        sources = []
        for source in project.get("sources", []):
            sources.append({
                "reference": source["reference"],
                "locator": source["locator"],
                "supports": source["supports"],
            })
        items.append({
            "project_id": project["project_id"],
            "project_name": project["project_name"],
            "utility": utility_name(project),
            "schedule": describe_schedule(project),
            "sources": sources,
        })
    return items


def explain(opportunity, projects_by_id):
    project_a = projects_by_id.get(opportunity["project_id_a"])
    project_b = projects_by_id.get(opportunity["project_id_b"])

    if project_a is None or project_b is None:
        raise ValueError(
            "Opportunity references a project that is not in /projects: "
            f"{opportunity['project_id_a']}, {opportunity['project_id_b']}"
        )
    if project_a["utility_id"] == project_b["utility_id"]:
        raise ValueError("Opportunity pairs two projects from the same utility.")

    category = classify(opportunity)

    return {
        "project_id_a": project_a["project_id"],
        "project_id_b": project_b["project_id"],
        "category": category["label"],
        "priority": category["priority"],
        "distance_miles": round(opportunity["distance_miles"], 2),
        "timeline_status": opportunity["timeline_status"],
        "why_flagged": why_flagged(opportunity, project_a, project_b),
        "uncertainties": uncertainties(opportunity, project_a, project_b),
        "evidence": evidence(project_a, project_b),
        "next_step": category["next_step"],
        "backend_reason": opportunity.get("reason"),
    }


# ---------------------------------------------------------------- empty case

def evidence_gaps(projects_by_id):
    """Counts what is missing, per utility, so the page can say exactly why
    there are no demonstrable opportunities."""
    gaps = []
    for utility_id, name in UTILITY_NAMES.items():
        records = [p for p in projects_by_id.values() if p["utility_id"] == utility_id]
        rankable = [
            p for p in records
            if p["review_status"] == "validated" and p.get("latitude") is not None
        ]
        no_coords = [p for p in records if p.get("latitude") is None]
        needs_review = [p for p in records if p["review_status"] != "validated"]
        no_end = [p for p in records if not p.get("construction_end")]

        gaps.append({
            "utility": name,
            "total_projects": len(records),
            "validated_with_coordinates": len(rankable),
            "missing_coordinates": len(no_coords),
            "needs_review": len(needs_review),
            "missing_construction_end": len(no_end),
        })
    return gaps


def empty_message(gaps):
    blocked = [g["utility"] for g in gaps if g["validated_with_coordinates"] == 0]
    message = (
        "No demonstrable coordination opportunities with the validated data. "
        "A pair can only be ranked when both projects are validated and have "
        "source-backed coordinates."
    )
    if blocked:
        message += (
            " Missing evidence: no validated records with coordinates for "
            + " and ".join(blocked) + "."
        )
    return message


# ---------------------------------------------------------------- main entry

def build_recommendations(opportunities, projects_by_id):
    gaps = evidence_gaps(projects_by_id)

    if not opportunities:
        return {
            "status": "no_demonstrable_opportunities",
            "summary": empty_message(gaps),
            "evidence_gaps": gaps,
            "recommendations": [],
        }

    # Keep the backend order (distance first); do not re-rank.
    recommendations = [explain(o, projects_by_id) for o in opportunities]

    counts = {}
    for rec in recommendations:
        counts[rec["category"]] = counts.get(rec["category"], 0) + 1
    summary = f"{len(recommendations)} cross-utility pairs within 25 miles: " + ", ".join(
        f"{n} {label.lower()}" for label, n in counts.items()
    ) + "."

    return {
        "status": "ok",
        "summary": summary,
        "evidence_gaps": gaps,
        "recommendations": recommendations,
    }


def self_test_data():
    """SYNTHETIC data to check the output format. Never shown as a real result."""
    projects = {
        "TEST_A": {
            "project_id": "TEST_A", "utility_id": "dominion_sc",
            "project_name": "Synthetic DESC project", "latitude": 32.0,
            "longitude": -81.0, "location_quality": "approximate",
            "location_method": "synthetic", "construction_start": "2027-01",
            "construction_end": None, "in_service_date": None,
            "schedule_text": None, "review_status": "validated",
            "sources": [{"reference": "synthetic-fixture", "locator": "test",
                         "supports": ["project_name"]}],
        },
        "TEST_B": {
            "project_id": "TEST_B", "utility_id": "georgia_power",
            "project_name": "Synthetic GPC project", "latitude": 32.1,
            "longitude": -81.1, "location_quality": "approximate",
            "location_method": "synthetic", "construction_start": None,
            "construction_end": None, "in_service_date": None,
            "schedule_text": "Need Date: 06/01/2030.", "review_status": "validated",
            "sources": [{"reference": "synthetic-fixture", "locator": "test",
                         "supports": ["project_name"]}],
        },
    }
    opportunities = [{
        "project_id_a": "TEST_A", "project_id_b": "TEST_B",
        "distance_miles": 8.7654, "distance_method": "postgis_geography",
        "location_uncertain": True, "timeline_status": "unknown",
        "reason": "synthetic",
    }]
    return projects, opportunities


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--self-test" in args:
        projects_by_id, opportunities = self_test_data()
        print("SYNTHETIC TEST - NOT A REAL RESULT")
    elif "--api" in args:
        api_url = args[args.index("--api") + 1]
        projects_by_id, opportunities = load_data(api_url)
    else:
        projects_by_id, opportunities = load_data()

    result = build_recommendations(opportunities, projects_by_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))