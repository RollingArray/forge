"""
Canonical vocabulary for FORGE specification authoring.

Keep accepted API values here so specification models, AI proposal
contracts and CSV import share the same definitions.
"""

from typing import Literal


FieldType = Literal[
    "IDENTIFIER",
    "STRING",
    "INTEGER",
    "DECIMAL",
    "BOOLEAN",
    "CATEGORICAL",
]

IdentityStrategy = Literal[
    "SEQUENTIAL_ID",
]

GenerationStrategy = Literal[
    "RANDOM",
]

Distribution = Literal[
    "UNIFORM",
    "CATEGORICAL",
    "DISCRETE_UNIFORM",
    "NORMAL",
    "POISSON",
]

StringGenerator = Literal[
    "RANDOM_STRING",
    "PATTERN",
    "SEMANTIC",
]

StringCharacterSet = Literal[
    "ALPHA",
    "DIGITS",
    "ALPHANUMERIC",
]

SemanticMode = Literal[
    "UNIQUE",
    "VOCABULARY",
]

RelationshipType = Literal[
    "ONE_TO_ONE",
    "ONE_TO_MANY",
    "MANY_TO_ONE",
    "MANY_TO_MANY",
]

RelationshipParticipation = Literal[
    "MANDATORY",
    "OPTIONAL",
]

ConstraintOperator = Literal[
    ">",
    ">=",
    "<",
    "<=",
    "==",
    "!=",
]
