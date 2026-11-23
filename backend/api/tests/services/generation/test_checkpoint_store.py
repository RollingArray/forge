import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.models.generation_persistence import (
    GenerationArtifactEvidence,
    GenerationFinalizationStatus,
)
from app.services.generation_checkpoint_store import (
    GenerationCheckpointStore,
    compute_specification_hash,
)
from app.services.generation_persistence_errors import (
    ArtifactIntegrityError,
    CheckpointCorruptError,
    CheckpointIdentityMismatchError,
    CheckpointValidationError,
)


MODEL_ID = "MODEL-TEST"
JOB_ID = "FORGE-TEST"
ATTEMPT_ID = "ATTEMPT-001"
SPECIFICATION = {"entities": [{"name": "CUSTOMER"}]}
SEED = 42
CHUNK_SIZE = 50
ALGORITHM_VERSION = "v1"


@pytest.fixture
def store(tmp_path, monkeypatch):
    instance = GenerationCheckpointStore()
    monkeypatch.setattr(instance, "_root", tmp_path)
    return instance


def initialize(store, targets=None):
    return store.initialize(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        specification=SPECIFICATION,
        seed=SEED,
        chunk_size=CHUNK_SIZE,
        algorithm_version=ALGORITHM_VERSION,
        attempt_id=ATTEMPT_ID,
        entity_targets=targets or {"CUSTOMER": 100},
    )


def write_artifact(store, relative_path, content):
    job_dir = store._job_directory(MODEL_ID, JOB_ID)
    artifact_path = job_dir / relative_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(content)

    return GenerationArtifactEvidence(
        path=relative_path,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def commit_chunk(
    store,
    *,
    chunk_number,
    row_start,
    row_count,
    content=None,
    attempt_id=ATTEMPT_ID,
):
    if content is None:
        content = f"chunk-{chunk_number}".encode()

    artifact = write_artifact(
        store,
        f"generated/customer/chunk-{chunk_number}.csv",
        content,
    )

    return store.commit_chunk(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=attempt_id,
        entity_name="CUSTOMER",
        chunk_number=chunk_number,
        row_start=row_start,
        row_count=row_count,
        artifact=artifact,
    )


def test_initialize_creates_typed_v2_manifest(store):
    manifest = initialize(store)

    assert manifest.schema_version == 2
    assert manifest.data_model_id == MODEL_ID
    assert manifest.job_id == JOB_ID
    assert manifest.attempt_id == ATTEMPT_ID
    assert manifest.specification_hash == compute_specification_hash(
        SPECIFICATION
    )
    assert manifest.entities["CUSTOMER"].target_rows == 100
    assert manifest.entities["CUSTOMER"].committed_rows == 0

    persisted = store.get(MODEL_ID, JOB_ID)
    assert persisted == manifest


def test_initialize_never_overwrites_existing_checkpoint(store):
    initialize(store)

    with pytest.raises(FileExistsError):
        initialize(store)


def test_missing_checkpoint_is_distinct_from_corrupt_checkpoint(store):
    assert store.get(MODEL_ID, JOB_ID) is None

    path = store._checkpoint_path(MODEL_ID, JOB_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(CheckpointCorruptError):
        store.get(MODEL_ID, JOB_ID)


def test_invalid_manifest_is_not_treated_as_missing(store):
    initialize(store)

    path = store._checkpoint_path(MODEL_ID, JOB_ID)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CheckpointValidationError):
        store.get(MODEL_ID, JOB_ID)


def test_specification_hash_is_order_independent_but_value_sensitive():
    original = {
        "entities": [
            {"name": "CUSTOMER", "fields": [{"name": "PRICE", "min": "0.1000"}]}
        ]
    }
    reordered = {
        "entities": [
            {"fields": [{"min": "0.1000", "name": "PRICE"}], "name": "CUSTOMER"}
        ]
    }
    different = {
        "entities": [
            {"name": "CUSTOMER", "fields": [{"name": "PRICE", "min": "0.1"}]}
        ]
    }

    assert compute_specification_hash(original) == compute_specification_hash(
        reordered
    )
    assert compute_specification_hash(original) != compute_specification_hash(
        different
    )


def test_commits_non_contiguous_chunks_and_derives_exact_rows(store):
    initialize(store, {"CUSTOMER": 150})

    commit_chunk(
        store,
        chunk_number=1,
        row_start=0,
        row_count=50,
    )
    commit_chunk(
        store,
        chunk_number=3,
        row_start=100,
        row_count=50,
    )

    assert store.get_committed_rows(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        entity_name="CUSTOMER",
    ) == 100

    assert store.is_chunk_committed(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        entity_name="CUSTOMER",
        chunk_number=3,
    )
    assert not store.is_chunk_committed(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        entity_name="CUSTOMER",
        chunk_number=2,
    )


def test_missing_checkpoint_has_zero_committed_rows(store):
    assert store.get_committed_rows(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        entity_name="CUSTOMER",
    ) == 0


def test_unknown_entity_is_not_reported_as_zero_progress(store):
    initialize(store)

    with pytest.raises(CheckpointValidationError):
        store.get_committed_rows(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            entity_name="UNKNOWN",
        )


def test_chunk_commit_is_idempotent_for_identical_evidence(store):
    initialize(store)

    first = commit_chunk(
        store,
        chunk_number=1,
        row_start=0,
        row_count=50,
    )
    second = commit_chunk(
        store,
        chunk_number=1,
        row_start=0,
        row_count=50,
    )

    assert first == second
    assert len(second.entities["CUSTOMER"].chunks) == 1


def test_chunk_commit_rejects_different_evidence_for_same_number(store):
    initialize(store)

    commit_chunk(
        store,
        chunk_number=1,
        row_start=0,
        row_count=50,
        content=b"first artifact",
    )

    with pytest.raises(CheckpointValidationError):
        commit_chunk(
            store,
            chunk_number=1,
            row_start=0,
            row_count=50,
            content=b"different artifact",
        )


def test_chunk_commit_rejects_missing_artifact(store):
    initialize(store)

    evidence = GenerationArtifactEvidence(
        path="generated/missing.csv",
        size_bytes=10,
        sha256=hashlib.sha256(b"0123456789").hexdigest(),
    )

    with pytest.raises(ArtifactIntegrityError):
        store.commit_chunk(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            attempt_id=ATTEMPT_ID,
            entity_name="CUSTOMER",
            chunk_number=1,
            row_start=0,
            row_count=50,
            artifact=evidence,
        )


def test_chunk_commit_rejects_artifact_size_mismatch(store):
    initialize(store)

    evidence = write_artifact(
        store,
        "generated/customer/chunk-1.csv",
        b"actual content",
    )
    incorrect = evidence.model_copy(update={"size_bytes": 999})

    with pytest.raises(ArtifactIntegrityError):
        store.commit_chunk(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            attempt_id=ATTEMPT_ID,
            entity_name="CUSTOMER",
            chunk_number=1,
            row_start=0,
            row_count=50,
            artifact=incorrect,
        )


def test_chunk_commit_rejects_artifact_hash_mismatch(store):
    initialize(store)

    evidence = write_artifact(
        store,
        "generated/customer/chunk-1.csv",
        b"actual content",
    )
    incorrect = evidence.model_copy(
        update={"sha256": hashlib.sha256(b"other content").hexdigest()}
    )

    with pytest.raises(ArtifactIntegrityError):
        store.commit_chunk(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            attempt_id=ATTEMPT_ID,
            entity_name="CUSTOMER",
            chunk_number=1,
            row_start=0,
            row_count=50,
            artifact=incorrect,
        )


def test_stale_attempt_cannot_commit_chunk(store):
    initialize(store)

    with pytest.raises(CheckpointIdentityMismatchError):
        commit_chunk(
            store,
            chunk_number=1,
            row_start=0,
            row_count=50,
            attempt_id="STALE-ATTEMPT",
        )


def test_stale_attempt_cannot_begin_finalization(store):
    initialize(store)

    with pytest.raises(CheckpointIdentityMismatchError):
        store.begin_finalization(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            attempt_id="STALE-ATTEMPT",
            entity_name="CUSTOMER",
        )


def test_stale_attempt_cannot_commit_finalization(store):
    initialize(store)

    with pytest.raises(CheckpointIdentityMismatchError):
        store.commit_finalization(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            attempt_id="STALE-ATTEMPT",
            entity_name="CUSTOMER",
            output=GenerationArtifactEvidence(
                path="generated/customer/final.csv",
                size_bytes=1,
                sha256=hashlib.sha256(b"x").hexdigest(),
            ),
        )


def test_supersede_attempt_preserves_chunks_and_resets_in_progress_finalization(store):
    initialize(store)

    commit_chunk(store, chunk_number=1, row_start=0, row_count=50)
    commit_chunk(store, chunk_number=2, row_start=50, row_count=50)

    before = store.begin_finalization(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name="CUSTOMER",
    )
    original_chunks = before.entities["CUSTOMER"].chunks

    assert (
        before.entities["CUSTOMER"].finalization.status
        == GenerationFinalizationStatus.IN_PROGRESS
    )

    updated = store.supersede_attempt(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        expected_attempt_id=ATTEMPT_ID,
        new_attempt_id="ATTEMPT-002",
    )

    entity = updated.entities["CUSTOMER"]

    assert updated.attempt_id == "ATTEMPT-002"
    assert entity.chunks == original_chunks
    assert entity.committed_rows == 100
    assert entity.finalization.status == GenerationFinalizationStatus.PENDING
    assert entity.finalization.output is None
    assert store.get(MODEL_ID, JOB_ID) == updated


def test_supersede_attempt_preserves_committed_finalization(store):
    initialize(store)

    commit_chunk(store, chunk_number=1, row_start=0, row_count=50)
    commit_chunk(store, chunk_number=2, row_start=50, row_count=50)

    store.begin_finalization(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name="CUSTOMER",
    )

    output = write_artifact(
        store,
        "generated/customer/final.csv",
        b"customer_id\n1\n",
    )

    before = store.commit_finalization(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name="CUSTOMER",
        output=output,
    )

    updated = store.supersede_attempt(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        expected_attempt_id=ATTEMPT_ID,
        new_attempt_id="ATTEMPT-002",
    )

    entity = updated.entities["CUSTOMER"]

    assert entity.chunks == before.entities["CUSTOMER"].chunks
    assert entity.finalization.status == GenerationFinalizationStatus.COMMITTED
    assert entity.finalization.output == output


def test_supersede_attempt_rejects_stale_expected_attempt(store):
    initialize(store)

    with pytest.raises(CheckpointIdentityMismatchError):
        store.supersede_attempt(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            expected_attempt_id="STALE-ATTEMPT",
            new_attempt_id="ATTEMPT-002",
        )

    assert store.get(MODEL_ID, JOB_ID).attempt_id == ATTEMPT_ID


def test_supersede_attempt_rejects_same_attempt_id(store):
    initialize(store)

    with pytest.raises(CheckpointValidationError):
        store.supersede_attempt(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            expected_attempt_id=ATTEMPT_ID,
            new_attempt_id=ATTEMPT_ID,
        )

    assert store.get(MODEL_ID, JOB_ID).attempt_id == ATTEMPT_ID


def test_finalization_requires_all_target_rows(store):
    initialize(store)

    commit_chunk(
        store,
        chunk_number=1,
        row_start=0,
        row_count=50,
    )

    with pytest.raises(CheckpointValidationError):
        store.begin_finalization(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            attempt_id=ATTEMPT_ID,
            entity_name="CUSTOMER",
        )


def test_finalization_transitions_to_committed(store):
    initialize(store)

    commit_chunk(
        store,
        chunk_number=1,
        row_start=0,
        row_count=50,
    )
    commit_chunk(
        store,
        chunk_number=2,
        row_start=50,
        row_count=50,
    )

    in_progress = store.begin_finalization(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name="CUSTOMER",
    )
    assert (
        in_progress.entities["CUSTOMER"].finalization.status
        == GenerationFinalizationStatus.IN_PROGRESS
    )

    output = write_artifact(
        store,
        "generated/customer/final.csv",
        b"customer_id\n1\n",
    )

    committed = store.commit_finalization(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name="CUSTOMER",
        output=output,
    )

    assert (
        committed.entities["CUSTOMER"].finalization.status
        == GenerationFinalizationStatus.COMMITTED
    )
    assert (
        committed.entities["CUSTOMER"].finalization.output == output
    )


def test_new_chunk_is_rejected_after_finalization_starts(store):
    initialize(store)

    commit_chunk(
        store,
        chunk_number=1,
        row_start=0,
        row_count=50,
    )
    commit_chunk(
        store,
        chunk_number=2,
        row_start=50,
        row_count=50,
    )

    store.begin_finalization(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name="CUSTOMER",
    )

    with pytest.raises(CheckpointValidationError):
        commit_chunk(
            store,
            chunk_number=3,
            row_start=100,
            row_count=1,
        )


def test_identical_chunk_retry_remains_idempotent_after_finalization_begins(
    store,
):
    initialize(store)

    first = commit_chunk(
        store,
        chunk_number=1,
        row_start=0,
        row_count=50,
    )

    commit_chunk(
        store,
        chunk_number=2,
        row_start=50,
        row_count=50,
    )

    store.begin_finalization(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name="CUSTOMER",
    )

    retry = commit_chunk(
        store,
        chunk_number=1,
        row_start=0,
        row_count=50,
    )

    assert retry == store.get(MODEL_ID, JOB_ID)
    assert len(retry.entities["CUSTOMER"].chunks) == 2


def test_committed_finalization_is_idempotent(store):
    initialize(store)

    commit_chunk(
        store,
        chunk_number=1,
        row_start=0,
        row_count=50,
    )
    commit_chunk(
        store,
        chunk_number=2,
        row_start=50,
        row_count=50,
    )

    store.begin_finalization(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name="CUSTOMER",
    )

    output = write_artifact(
        store,
        "generated/customer/final.csv",
        b"customer_id\n1\n",
    )

    first = store.commit_finalization(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name="CUSTOMER",
        output=output,
    )
    second = store.commit_finalization(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name="CUSTOMER",
        output=output,
    )

    assert first == second


def test_validate_identity_checks_every_identity_component(store):
    manifest = initialize(store)

    store.validate_identity(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        specification_hash=manifest.specification_hash,
        seed=SEED,
        chunk_size=CHUNK_SIZE,
        algorithm_version=ALGORITHM_VERSION,
        attempt_id=ATTEMPT_ID,
    )

    with pytest.raises(CheckpointIdentityMismatchError):
        store.validate_identity(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            specification_hash=manifest.specification_hash,
            seed=SEED,
            chunk_size=CHUNK_SIZE,
            algorithm_version=ALGORITHM_VERSION,
            attempt_id="STALE-ATTEMPT",
        )


@pytest.mark.parametrize(
    "identifier",
    [
        "../escape",
        "nested/path",
        r"nested\\path",
        "CON",
        "con.txt",
        "NUL",
        "COM1",
        "LPT9",
        "trailing.",
        "trailing ",
        "invalid:name",
    ],
)
def test_path_components_reject_nonportable_identifiers(store, identifier):
    with pytest.raises(ValueError):
        store._checkpoint_path(identifier, JOB_ID)

    with pytest.raises(ValueError):
        store._checkpoint_path(MODEL_ID, identifier)


def test_concurrent_chunk_commits_do_not_lose_updates(store):
    initialize(store, {"CUSTOMER": 200})

    def commit(number):
        return commit_chunk(
            store,
            chunk_number=number,
            row_start=(number - 1) * CHUNK_SIZE,
            row_count=CHUNK_SIZE,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(commit, [1, 2, 3, 4]))

    manifest = store.get(MODEL_ID, JOB_ID)
    entity = manifest.entities["CUSTOMER"]

    assert [chunk.chunk_number for chunk in entity.chunks] == [1, 2, 3, 4]
    assert entity.committed_rows == 200
    assert store.get_committed_rows(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        entity_name="CUSTOMER",
    ) == 200
