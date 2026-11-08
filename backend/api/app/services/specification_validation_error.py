from typing import Any


class SpecificationValidationError(Exception):
    """Raised when a canonical specification fails validation."""

    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.findings = result.get("findings", [])

        errors = result.get("errors", 0)
        super().__init__(
            f"Specification validation failed with {errors} error(s)."
        )
