"""Request and response contracts for iterative prompt refinement."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AIPromptRefinementRequestModel(BaseModel):
    """User-provided business description to refine before specification authoring."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=20000)


class AIPromptRefinementQuestionModel(BaseModel):
    """A targeted question to resolve an ambiguity or missing requirement."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=1, max_length=2000)
    answer_type: Literal[
        "yes_no",
        "integer",
        "decimal",
        "text",
        "field",
        "operator",
        "choice",
    ]
    options: list[str] = Field(default_factory=list, max_length=50)
    suggested_answer: str | None = Field(default=None, max_length=2000)
    recommendation_rationale: str | None = Field(default=None, max_length=1000)
    required: bool


class AIPromptRefinementResponseModel(BaseModel):
    """Structured result of refining a business description."""

    model_config = ConfigDict(extra="forbid")

    refined_prompt: str = Field(min_length=1, max_length=20000)
    completeness_status: Literal[
        "INCOMPLETE",
        "NEEDS_REVIEW",
        "READY_FOR_SPECIFICATION",
    ]
    summary: str = Field(min_length=1, max_length=4000)
    understood_requirements: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[AIPromptRefinementQuestionModel] = Field(
        default_factory=list
    )
    missing_requirements: list[str] = Field(default_factory=list)
