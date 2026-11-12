import json

from app.repositories.json_specification_repository import (
    JsonSpecificationRepository,
)


def test_decimal_strings_survive_specification_save_and_reload(
    tmp_path,
    monkeypatch,
):
    repository = JsonSpecificationRepository()
    monkeypatch.setattr(repository, "_data_directory", tmp_path)

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "fields": [
                    {
                        "name": "PRICE",
                        "type": "DECIMAL",
                        "generation": {
                            "min": "0.1000",
                            "max": "999999999999999999.123400",
                        },
                    }
                ],
            }
        ]
    }

    repository.save("MODEL-DECIMAL", specification)
    reloaded = repository.read("MODEL-DECIMAL")

    assert reloaded == specification

    persisted = json.loads(
        (
            tmp_path
            / "data_model"
            / "MODEL-DECIMAL"
            / "specification.json"
        ).read_text(encoding="utf-8")
    )

    generation = persisted["entities"][0]["fields"][0]["generation"]
    assert generation["min"] == "0.1000"
    assert generation["max"] == "999999999999999999.123400"


def test_specification_revision_distinguishes_decimal_representation():
    base = {
        "entities": [
            {
                "fields": [
                    {
                        "name": "PRICE",
                        "type": "DECIMAL",
                        "generation": {"min": "0.1"},
                    }
                ]
            }
        ]
    }
    with_trailing_zeros = {
        "entities": [
            {
                "fields": [
                    {
                        "name": "PRICE",
                        "type": "DECIMAL",
                        "generation": {"min": "0.1000"},
                    }
                ]
            }
        ]
    }

    assert (
        JsonSpecificationRepository.revision(base)
        != JsonSpecificationRepository.revision(with_trailing_zeros)
    )
