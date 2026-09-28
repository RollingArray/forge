from pydantic import BaseModel, ConfigDict, Field, field_validator


class PopulationTargetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: int = Field(ge=1)
    driver: str = Field(min_length=1)

    @field_validator("target", mode="before")
    @classmethod
    def validate_target(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("target must be an integer.")
        return value

    @field_validator("driver", mode="before")
    @classmethod
    def validate_driver(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("driver must be a string.")
        return value.strip()


class AcceptPopulationPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    populations: dict[str, int]
