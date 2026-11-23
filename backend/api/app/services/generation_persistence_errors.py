"""Domain exceptions for generation persistence and artifact integrity."""


class GenerationPersistenceError(RuntimeError):
    """Base class for generation persistence failures."""


class PersistenceOperationError(GenerationPersistenceError):
    """A filesystem persistence operation failed."""


class CheckpointError(GenerationPersistenceError):
    """Base class for checkpoint failures."""


class CheckpointNotFoundError(CheckpointError):
    """The requested checkpoint does not exist."""


class CheckpointCorruptError(CheckpointError):
    """The checkpoint cannot be parsed or is structurally corrupt."""


class CheckpointValidationError(CheckpointError):
    """The checkpoint violates the persistence schema or invariants."""


class CheckpointIdentityMismatchError(CheckpointError):
    """The checkpoint belongs to a different generation identity."""


class ArtifactIntegrityError(GenerationPersistenceError):
    """A persisted artifact is missing or fails integrity verification."""


class JobRecordCorruptError(GenerationPersistenceError):
    """A persisted job record contains invalid or unreadable content."""


class JobRecordValidationError(GenerationPersistenceError):
    """A persisted job record violates its schema or identity."""
