from src.nodos_funcionales.user_curated_scoring_approval import (
    REQUIRED_ACKNOWLEDGEMENTS,
    approval_allows_controlled_scoring,
    summarize_scoring_approval,
    validate_scoring_approval,
)


def valid_record():
    return {
        "dataset_id": "user_dataset_001",
        "organism": "User defined organism",
        "strain_or_lineage": "User defined strain",
        "reviewer_name": "Expert Reviewer",
        "reviewer_role": "Domain expert",
        "review_date": "2026-05-21",
        "quality_gate_decision": "conditionally_ready_for_future_controlled_scoring",
        "approval_status": "approved_for_controlled_scoring",
        "approval_scope": "Controlled scoring preparation only.",
        "notes": "Reviewed for provenance, completeness and interpretive limits.",
        "provenance_summary": "User-curated evidence with traceable sources.",
        "primary_evidence_type": "user_curated",
        "explicit_acknowledgements": {
            key: True for key in REQUIRED_ACKNOWLEDGEMENTS
        },
    }


def test_valid_approval_allows_controlled_scoring():
    record = valid_record()

    result = validate_scoring_approval(record)

    assert result["valid"] is True
    assert result["allows_controlled_scoring"] is True
    assert result["errors"] == []
    assert approval_allows_controlled_scoring(record) is True


def test_missing_approval_blocks_controlled_scoring():
    result = validate_scoring_approval({})

    assert result["valid"] is False
    assert result["allows_controlled_scoring"] is False
    assert "dataset_id is required." in result["errors"]
    assert "organism is required." in result["errors"]


def test_not_approved_status_blocks_controlled_scoring():
    record = valid_record()
    record["approval_status"] = "not_approved"

    result = validate_scoring_approval(record)

    assert result["allows_controlled_scoring"] is False
    assert "approval_status must be approved_for_controlled_scoring." in result["errors"]
    assert "approval_status explicitly blocks scoring: not_approved." in result["errors"]


def test_rejected_status_blocks_controlled_scoring():
    record = valid_record()
    record["approval_status"] = "rejected_for_scoring"

    result = validate_scoring_approval(record)

    assert result["allows_controlled_scoring"] is False
    assert "approval_status explicitly blocks scoring: rejected_for_scoring." in result["errors"]


def test_requires_additional_curation_blocks_controlled_scoring():
    record = valid_record()
    record["approval_status"] = "requires_additional_curation"

    result = validate_scoring_approval(record)

    assert result["allows_controlled_scoring"] is False
    assert (
        "approval_status explicitly blocks scoring: requires_additional_curation."
        in result["errors"]
    )


def test_not_ready_quality_gate_blocks_controlled_scoring():
    record = valid_record()
    record["quality_gate_decision"] = "not_ready_for_scoring"

    result = validate_scoring_approval(record)

    assert result["allows_controlled_scoring"] is False
    assert (
        "quality_gate_decision blocks controlled scoring because the dataset is not ready."
        in result["errors"]
    )


def test_missing_acknowledgements_block_controlled_scoring():
    record = valid_record()
    record["explicit_acknowledgements"] = {
        "scoring_is_not_biological_validation": True
    }

    result = validate_scoring_approval(record)

    assert result["allows_controlled_scoring"] is False
    assert result["missing_acknowledgements"]
    assert any(
        error.startswith("required acknowledgement missing or false:")
        for error in result["errors"]
    )


def test_placeholders_block_controlled_scoring():
    record = valid_record()
    record["dataset_id"] = "replace_me"
    record["organism"] = "placeholder"

    result = validate_scoring_approval(record)

    assert result["allows_controlled_scoring"] is False
    assert "dataset_id is required." in result["errors"]
    assert "organism is required." in result["errors"]


def test_demo_proxy_cache_cannot_be_primary_evidence():
    record = valid_record()
    record["primary_evidence_type"] = "demo"

    result = validate_scoring_approval(record)

    assert result["allows_controlled_scoring"] is False
    assert (
        "demo, proxy, cache, template or example data cannot be primary evidence."
        in result["errors"]
    )


def test_provenance_mentions_cache_as_warning_not_primary_evidence():
    record = valid_record()
    record["provenance_summary"] = (
        "User-curated evidence reviewed against cache only for comparison."
    )

    result = validate_scoring_approval(record)

    assert result["allows_controlled_scoring"] is True
    assert result["warnings"]


def test_summary_is_conservative():
    record = valid_record()

    summary = summarize_scoring_approval(record)

    assert "Allows controlled scoring: True" in summary
    assert "This approval does not validate biology." in summary
    assert "This approval does not validate clinical use." in summary
    assert "not a therapeutic recommendation" in summary
    assert "high therapeutic priority score" in summary
    assert "Incomplete evidence must not be interpreted as low risk." in summary
