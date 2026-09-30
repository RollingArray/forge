import json

from app.services.ollama_ai_provider import OllamaAIProvider


def _provider(monkeypatch, responses):
    class FakeResponse:
        def __init__(self, content):
            self.content = content.encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return self.content

    calls = []

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data.decode()))
        return FakeResponse(
            json.dumps(
                {
                    "message": {
                        "content": json.dumps(
                            {"values": responses.pop(0)}
                        )
                    }
                }
            )
        )

    monkeypatch.setattr(
        "app.services.ollama_ai_provider.urlopen",
        fake_urlopen,
    )

    from app.services.ollama_ai_provider import AIConfiguration

    return OllamaAIProvider(
        AIConfiguration(
            provider="ollama",
            base_url="http://localhost:11434",
            model="gpt-oss:20b",
            capability_timeout_seconds=2.0,
            generation_timeout_seconds=180.0,
        )
    ), calls


def test_semantic_generation_trims_excess_values(monkeypatch):
    values = [f"Product {i}" for i in range(53)]

    provider, calls = _provider(monkeypatch, [values])

    result = provider.generate_semantic_values(
        description="Realistic aerospace product name.",
        mode="UNIQUE",
        count=50,
    )

    assert len(result) == 50
    assert result == values[:50]
    assert len(calls) == 1


def test_semantic_generation_refills_missing_values(monkeypatch):
    first = [f"Product {i}" for i in range(49)]
    refill = ["Product 49"]

    provider, calls = _provider(monkeypatch, [first, refill])

    result = provider.generate_semantic_values(
        description="Realistic aerospace product name.",
        mode="UNIQUE",
        count=50,
    )

    assert len(result) == 50
    assert result == [*first, *refill]
    assert len(calls) == 2
    assert "Count: 1" in calls[1]["messages"][1]["content"]
