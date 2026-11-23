from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.generation_persistence import (
    GenerationArtifactEvidence,
    GenerationCheckpointManifest,
    GenerationChunkEvidence,
    GenerationEntityCheckpoint,
    GenerationFinalization,
    GenerationFinalizationStatus,
)


NOW = datetime(2026, 11, 21, 10, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def artifact(path: str = "chunks/CUSTOMER/chunk-0001.csv"):
    return GenerationArtifactEvidence(
        path=path,
        size_bytes=1024,
        sha256=HASH,
    )


def chunk(
    number: int = 1,
    row_start: int = 0,
    row_count: int = 50,
):
    return GenerationChunkEvidence(
        chunk_number=number,
        row_start=row_start,
        row_count=row_count,
        artifact=artifact(
            f"chunks/CUSTOMER/chunk-{number:04d}.csv"
        ),
        committed_at=NOW,
    )


def manifest(
    *,
    chunks=None,
    target_rows=100,
    finalization=None,
):
    return GenerationCheckpointManifest(
        schema_version=2,
        data_model_id="MODEL-TEST",
        job_id="JOB-TEST",
        specification_hash=HASH,
        seed=42,
        chunk_size=50,
        algorithm_version="forge-generation-v1",
        attempt_id="attempt-001",
        entities={
            "CUSTOMER": GenerationEntityCheckpoint(
                target_rows=target_rows,
                chunks=chunks or [],
                finalization=finalization or GenerationFinalization(),
            )
        },
        created_at=NOW,
        updated_at=NOW,
    )


def test_valid_v2_manifest_is_accepted():
    result = manifest(chunks=[chunk()])

    assert result.schema_version == 2
    assert result.data_model_id == "MODEL-TEST"
    assert result.entities["CUSTOMER"].committed_rows == 50


def test_committed_rows_are_derived_from_exact_chunk_row_counts():
    result = manifest(
        chunks=[
            chunk(number=1, row_start=0, row_count=50),
            chunk(number=2, row_start=50, row_count=25),
        ],
        target_rows=75,
    )

    assert result.entities["CUSTOMER"].committed_rows == 75


def test_non_contiguous_chunks_are_valid_when_identity_and_ranges_match():
    result = manifest(
        chunks=[
            chunk(number=1, row_start=0, row_count=50),
            chunk(number=3, row_start=100, row_count=25),
        ],
        target_rows=125,
    )

    assert result.entities["CUSTOMER"].committed_rows == 75


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/absolute/file.csv",
        "../outside.csv",
        "chunks/../outside.csv",
        "chunks\\CUSTOMER\\chunk.csv",
        "chunks//CUSTOMER.csv",
        "./chunk.csv",
        "C:/chunks/chunk.csv",
    ],
)
def test_artifact_path_rejects_nonportable_or_unsafe_paths(path):
    with pytest.raises(ValidationError):
        artifact(path)


def test_artifact_hash_must_be_sha256():
    with pytest.raises(ValidationError):
        GenerationArtifactEvidence(
            path="chunks/file.csv",
            size_bytes=100,
            sha256="not-a-hash",
        )


def test_artifact_size_must_be_positive():
    with pytest.raises(ValidationError):
        GenerationArtifactEvidence(
            path="chunks/file.csv",
            size_bytes=0,
            sha256=HASH,
        )


def test_duplicate_chunk_numbers_are_rejected():
    with pytest.raises(ValidationError, match="unique"):
        manifest(
            chunks=[
                chunk(number=1, row_start=0),
                chunk(number=1, row_start=0),
            ]
        )


def test_chunks_must_be_ordered_by_chunk_number():
    with pytest.raises(ValidationError, match="ordered"):
        manifest(
            chunks=[
                chunk(number=2, row_start=50),
                chunk(number=1, row_start=0),
            ]
        )


def test_overlapping_chunk_ranges_are_rejected():
    with pytest.raises(ValidationError, match="overlap"):
        GenerationEntityCheckpoint(
            target_rows=100,
            chunks=[
                chunk(number=1, row_start=0, row_count=50),
                chunk(number=2, row_start=25, row_count=50),
            ],
        )


def test_chunk_row_start_must_match_chunk_identity():
    with pytest.raises(ValidationError, match="must start at row 50"):
        manifest(
            chunks=[
                chunk(number=2, row_start=25, row_count=25),
            ]
        )


def test_chunk_cannot_exceed_configured_chunk_size():
    with pytest.raises(ValidationError, match="must contain exactly 50 rows"):
        manifest(
            chunks=[
                chunk(number=1, row_start=0, row_count=51),
            ]
        )


def test_chunk_cannot_exceed_entity_target():
    with pytest.raises(ValidationError, match="exceed the entity target"):
        manifest(
            chunks=[
                chunk(number=1, row_start=0, row_count=50),
                chunk(number=2, row_start=50, row_count=50),
            ],
            target_rows=75,
        )


def test_committed_finalization_requires_output_evidence():
    with pytest.raises(ValidationError, match="requires consolidated output"):
        GenerationFinalization(
            status=GenerationFinalizationStatus.COMMITTED,
        )


def test_uncommitted_finalization_cannot_have_output_evidence():
    with pytest.raises(ValidationError, match="only valid for committed"):
        GenerationFinalization(
            status=GenerationFinalizationStatus.IN_PROGRESS,
            output=artifact("output/CUSTOMER.csv"),
        )


def test_entity_cannot_finalize_before_all_target_rows_are_committed():
    with pytest.raises(ValidationError, match="all target rows"):
        manifest(
            chunks=[chunk(number=1, row_start=0, row_count=50)],
            target_rows=100,
            finalization=GenerationFinalization(
                status=GenerationFinalizationStatus.COMMITTED,
                output=artifact("output/CUSTOMER.csv"),
            ),
        )


def test_committed_finalization_is_valid_when_all_rows_are_committed():
    result = manifest(
        chunks=[
            chunk(number=1, row_start=0, row_count=50),
            chunk(number=2, row_start=50, row_count=50),
        ],
        target_rows=100,
        finalization=GenerationFinalization(
            status=GenerationFinalizationStatus.COMMITTED,
            output=artifact("output/CUSTOMER.csv"),
        ),
    )

    assert (
        result.entities["CUSTOMER"].finalization.status
        == GenerationFinalizationStatus.COMMITTED
    )


def test_naive_timestamps_are_rejected():
    payload = manifest().model_dump()
    payload["created_at"] = datetime(2026, 11, 21, 10, 0)

    with pytest.raises(ValidationError, match="timezone"):
        GenerationCheckpointManifest.model_validate(payload)


def test_unknown_manifest_fields_are_rejected():
    payload = manifest().model_dump()
    payload["unexpected"] = "not allowed"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        GenerationCheckpointManifest.model_validate(payload)


def test_schema_version_one_is_rejected():
    payload = manifest().model_dump()
    payload["schema_version"] = 1

    with pytest.raises(ValidationError):
        GenerationCheckpointManifest.model_validate(payload)


def test_boolean_values_are_not_accepted_as_integer_seed_or_chunk_size():
    payload = manifest().model_dump()
    payload["seed"] = True

    with pytest.raises(ValidationError):
        GenerationCheckpointManifest.model_validate(payload)


def test_updated_at_cannot_precede_created_at():
    payload = manifest().model_dump()
    payload["updated_at"] = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="earlier than created_at"):
        GenerationCheckpointManifest.model_validate(payload)



def test_non_final_chunk_must_contain_full_chunk_size():
    with pytest.raises(ValidationError, match="must contain exactly 50 rows"):
        manifest(
            chunks=[
                chunk(number=1, row_start=0, row_count=25),
                chunk(number=2, row_start=50, row_count=50),
            ],
            target_rows=100,
        )


def test_final_chunk_may_contain_remaining_rows():
    result = manifest(
        chunks=[
            chunk(number=1, row_start=0, row_count=50),
            chunk(number=2, row_start=50, row_count=25),
        ],
        target_rows=75,
    )

    assert result.entities["CUSTOMER"].committed_rows == 75


def test_finalization_cannot_hide_a_gap_in_committed_row_ranges():
    with pytest.raises(ValidationError, match="all target rows"):
        manifest(
            chunks=[
                chunk(number=1, row_start=0, row_count=25),
                chunk(number=2, row_start=50, row_count=25),
            ],
            target_rows=75,
            finalization=GenerationFinalization(
                status=GenerationFinalizationStatus.COMMITTED,
                output=artifact("output/CUSTOMER.csv"),
            ),
        )


def test_artifact_paths_must_be_unique_across_chunks():
    duplicate_path = "chunks/CUSTOMER/shared.csv"

    with pytest.raises(ValidationError, match="collides"):
        manifest(
            chunks=[
                GenerationChunkEvidence(
                    chunk_number=1,
                    row_start=0,
                    row_count=50,
                    artifact=artifact(duplicate_path),
                    committed_at=NOW,
                ),
                GenerationChunkEvidence(
                    chunk_number=2,
                    row_start=50,
                    row_count=50,
                    artifact=artifact(duplicate_path),
                    committed_at=NOW,
                ),
            ],
            target_rows=100,
        )


def test_final_output_path_must_not_duplicate_a_chunk_path():
    with pytest.raises(ValidationError, match="collides"):
        manifest(
            chunks=[
                chunk(number=1, row_start=0, row_count=50),
                chunk(number=2, row_start=50, row_count=50),
            ],
            target_rows=100,
            finalization=GenerationFinalization(
                status=GenerationFinalizationStatus.COMMITTED,
                output=artifact("chunks/CUSTOMER/chunk-0001.csv"),
            ),
        )



@pytest.mark.parametrize(
    "path",
    [
        "chunks/CON.csv",
        "chunks/NUL",
        "chunks/COM1.csv",
        "chunks/LPT9.csv",
        "chunks/file?.csv",
        "chunks/file*.csv",
        "chunks/file>.csv",
        "chunks/file|.csv",
        "chunks/trailing.",
        "chunks/trailing ",
        "chunks/control\x01.csv",
    ],
)
def test_artifact_path_rejects_windows_invalid_names(path):
    with pytest.raises(ValidationError):
        artifact(path)


def test_artifact_path_rejects_non_nfc_unicode():
    with pytest.raises(ValidationError, match="NFC"):
        artifact("chunks/cafe\u0301.csv")


def test_artifact_paths_are_unique_case_insensitively():
    with pytest.raises(ValidationError, match="collides"):
        manifest(
            chunks=[
                GenerationChunkEvidence(
                    chunk_number=1,
                    row_start=0,
                    row_count=50,
                    artifact=artifact("chunks/CUSTOMER.csv"),
                    committed_at=NOW,
                ),
                GenerationChunkEvidence(
                    chunk_number=2,
                    row_start=50,
                    row_count=50,
                    artifact=artifact("chunks/customer.csv"),
                    committed_at=NOW,
                ),
            ],
            target_rows=100,
        )


def test_final_output_path_is_checked_case_insensitively():
    with pytest.raises(ValidationError, match="collides"):
        manifest(
            chunks=[
                chunk(number=1, row_start=0, row_count=50),
                chunk(number=2, row_start=50, row_count=50),
            ],
            target_rows=100,
            finalization=GenerationFinalization(
                status=GenerationFinalizationStatus.COMMITTED,
                output=artifact("CHUNKS/CUSTOMER/CHUNK-0001.CSV"),
            ),
        )
