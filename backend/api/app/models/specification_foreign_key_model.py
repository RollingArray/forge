from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateForeignKeyRequest(BaseModel):
    """Request to create a deterministic FORGE foreign key."""

    model_config = ConfigDict(extra="forbid")

    source_entity: str = Field(min_length=1)
    source_fields: list[str] = Field(min_length=1)
    target_entity: str = Field(min_length=1)

    @field_validator("source_entity", "target_entity")
    @classmethod
    def validate_entity_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Entity name must not be empty.")

        return value

    @field_validator("source_fields")
    @classmethod
    def validate_source_fields(
        cls,
        value: list[str],
    ) -> list[str]:
        normalized = []

        for field_name in value:
            if not isinstance(field_name, str):
                raise ValueError(
                    "source_fields must contain strings."
                )

            field_name = field_name.strip()

            if not field_name:
                raise ValueError(
                    "source_fields must not contain empty names."
                )

            normalized.append(field_name)

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "source_fields must not contain duplicates."
            )

        return normalized

class ExistingForeignKeyRequest(BaseModel):
    """Identify an existing FORGE foreign key by name."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Foreign key name must not be empty.")

        return value


class UpdateForeignKeyRequest(BaseModel):
    """Request to replace an existing deterministic foreign key mapping."""

    model_config = ConfigDict(extra="forbid")

    existing: ExistingForeignKeyRequest
    foreign_key: CreateForeignKeyRequest

