import copy
import json
from pathlib import Path

import pytest

from gridlock_importer.validation import BatchValidationError, validate_batch


SAMPLE_PATH = Path(__file__).parents[1] / "examples" / "projects.sample.json"


@pytest.fixture
def sample_batch() -> dict:
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def test_sample_batch_is_valid(sample_batch: dict) -> None:
    projects = validate_batch(sample_batch)

    assert [project["project_id"] for project in projects] == [
        "fixture-dominion-001"
    ]


def test_duplicate_project_ids_are_rejected(sample_batch: dict) -> None:
    sample_batch["projects"].append(copy.deepcopy(sample_batch["projects"][0]))

    with pytest.raises(BatchValidationError, match="duplicate project IDs"):
        validate_batch(sample_batch)


def test_invalid_partial_date_is_rejected(sample_batch: dict) -> None:
    sample_batch["projects"][0]["in_service_date"] = "2026-02-30"

    with pytest.raises(BatchValidationError, match="day is out of range"):
        validate_batch(sample_batch)


def test_coordinate_pair_is_required(sample_batch: dict) -> None:
    sample_batch["projects"][0]["latitude"] = 33.5

    with pytest.raises(BatchValidationError, match="must both be set"):
        validate_batch(sample_batch)
