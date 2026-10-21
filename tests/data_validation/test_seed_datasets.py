import json
import re
from pathlib import Path
import pytest
from redllm.strategies.alternate_role.templates import ROLE_PERSONAS, MODE_NAMES


DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "evaluation" / "datasets"


def test_jailbreak_seed_json_structure_and_required_fields():
    """
    Requirement 9: Data validation for jailbreak_seed.json:
    - confirm every entry has the required fields
    - confirm expected-outcome field only contains allowed values
    - confirm there are no duplicate identifiers
    - confirm template placeholders have corresponding values available at generation time
    """
    seed_file = DATASETS_DIR / "jailbreak_seed.json"
    assert seed_file.exists(), f"Seed file {seed_file} not found"

    with open(seed_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "seed_version" in data
    assert "seeds" in data and isinstance(data["seeds"], list)
    assert "benign_seeds" in data and isinstance(data["benign_seeds"], list)

    all_ids = set()
    allowed_expected_behaviors = {"blocked", "allowed"}
    allowed_components = {"guard", "target", "both"}
    
    # Recognized placeholder parameters available during test prompt generation
    known_generation_placeholders = {
        "role_name",
        "mode_name",
        "objective",
        "encoded_objective",
        "role_description"
    }

    # Verify personas and modes exist in templates module
    assert len(ROLE_PERSONAS) > 0
    assert len(MODE_NAMES) > 0

    # 1. Validate malicious seeds
    required_malicious_fields = [
        "id", "category", "subcategory", "prompt", "target_component", "expected_behavior"
    ]
    for seed in data["seeds"]:
        # Required fields check
        for field in required_malicious_fields:
            assert field in seed, f"Seed entry missing required field '{field}': {seed}"
            assert seed[field] is not None, f"Field '{field}' cannot be None in {seed['id']}"
            if isinstance(seed[field], str):
                assert seed[field].strip() != "", f"Field '{field}' cannot be empty string in {seed['id']}"

        # Duplicate ID check
        assert seed["id"] not in all_ids, f"Duplicate identifier found: {seed['id']}"
        all_ids.add(seed["id"])

        # Expected behavior allowed values check
        assert seed["expected_behavior"] in allowed_expected_behaviors, (
            f"Invalid expected_behavior '{seed['expected_behavior']}' in {seed['id']}. "
            f"Allowed: {allowed_expected_behaviors}"
        )

        # Target component allowed values check
        assert seed["target_component"] in allowed_components, (
            f"Invalid target_component '{seed['target_component']}' in {seed['id']}"
        )

        # Placeholder availability check
        placeholders = re.findall(r"\{([a-zA-Z0-9_]+)\}", seed["prompt"])
        for ph in placeholders:
            assert ph in known_generation_placeholders, (
                f"Unknown placeholder '{{{ph}}}' in {seed['id']}. "
                f"Not available in known generation variables: {known_generation_placeholders}"
            )

    # 2. Validate benign seeds
    required_benign_fields = [
        "id", "category", "subcategory", "prompt", "target_component", "expected_behavior"
    ]
    for b_seed in data["benign_seeds"]:
        for field in required_benign_fields:
            assert field in b_seed, f"Benign seed missing required field '{field}': {b_seed}"
            assert b_seed[field] is not None and str(b_seed[field]).strip() != ""

        assert b_seed["id"] not in all_ids, f"Duplicate identifier across seeds found: {b_seed['id']}"
        all_ids.add(b_seed["id"])

        assert b_seed["expected_behavior"] in allowed_expected_behaviors
        assert b_seed["expected_behavior"] == "allowed", (
            f"Benign seed {b_seed['id']} must have expected_behavior='allowed'"
        )


def test_companion_dataset_files_validation():
    """Confirm jailbreaks.json, system_leaks.json, and tool_abuse.json have valid structures and unique IDs."""
    files_to_check = {
        "jailbreaks.json": ["id", "objective", "prompt", "attack_type"],
        "system_leaks.json": ["id", "objective", "prompt", "attack_type"],
        "tool_abuse.json": ["id", "objective", "prompt", "attack_type", "target_tool"]
    }

    for fname, req_fields in files_to_check.items():
        fpath = DATASETS_DIR / fname
        assert fpath.exists(), f"Dataset file {fname} not found at {fpath}"

        with open(fpath, "r", encoding="utf-8") as f:
            entries = json.load(f)

        assert isinstance(entries, list)
        assert len(entries) > 0

        seen_ids = set()
        for item in entries:
            for field in req_fields:
                assert field in item, f"Missing field '{field}' in {fname} item: {item}"
                assert item[field] is not None
            assert item["id"] not in seen_ids, f"Duplicate ID '{item['id']}' in {fname}"
            seen_ids.add(item["id"])
