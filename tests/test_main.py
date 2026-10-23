# tests/test_main.py
from typing import Any

import pytest

from genpass.main import (
    SPANISH_WORDLIST_URL,
    generate_passphrase,
    generate_password,
    load_portuguese_words,
    load_spanish_words,
)


@pytest.fixture
def mock_secrets_choice(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Mock secrets.choice using pytest's monkeypatch."""
    calls: list[Any] = []

    def mock_choice(seq: Any) -> Any:
        calls.append(seq)
        return seq[0]

    monkeypatch.setattr("secrets.choice", mock_choice)
    return calls


@pytest.fixture
def mock_secrets_system_random(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Mock secrets.SystemRandom using pytest's monkeypatch."""
    shuffle_calls: list[Any] = []

    class MockSystemRandom:
        def shuffle(self, x: list[Any]) -> None:
            shuffle_calls.append(x)

    monkeypatch.setattr("secrets.SystemRandom", MockSystemRandom)
    return shuffle_calls


@pytest.fixture
def mock_urlopen_success(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Mock urllib.request.urlopen for successful network calls using pytest's monkeypatch."""
    calls: list[dict[str, Any]] = []

    class MockResponse:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        def __enter__(self) -> "MockResponse":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self) -> bytes:
            return self._payload

    def mock_urlopen(url: str, timeout: int | None = None) -> MockResponse:
        calls.append({"url": url, "timeout": timeout})
        payload = b"Abacaxi\nJanela\nCripto123\nSol\n"
        return MockResponse(payload)

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    return calls


@pytest.fixture
def mock_urlopen_failure(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Mock urllib.request.urlopen for failed network calls using pytest's monkeypatch."""
    calls: list[dict[str, Any]] = []

    def mock_urlopen(url: str, timeout: int | None = None) -> Any:
        calls.append({"url": url, "timeout": timeout})
        raise OSError("Network is unreachable")

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    return calls


def test_load_portuguese_words_network_success(mock_urlopen_success: list[dict[str, Any]]) -> None:
    """Verify clean downstream sanitization paths when remote streams load normally."""
    words = load_portuguese_words()

    # Should lowercase valid strings and drop those out of character limits
    assert "abacaxi" in words
    assert "janela" in words
    assert "sol" not in words  # Less than 4 characters
    assert len(mock_urlopen_success) == 1
    assert mock_urlopen_success[0]["timeout"] == 5


def test_load_portuguese_words_network_failure(mock_urlopen_failure: list[dict[str, Any]]) -> None:
    """Verify bulletproof fallback array triggers instantly on systemic socket timeouts."""
    words = load_portuguese_words()

    assert "computador" in words
    assert len(words) == 10
    assert len(mock_urlopen_failure) == 1


def test_load_spanish_words_network_success(mock_urlopen_success: list[dict[str, Any]]) -> None:
    """Verify the Spanish loader hits the Spanish source and applies the same sanitization."""
    words = load_spanish_words()

    assert "abacaxi" in words
    assert "janela" in words
    assert "sol" not in words  # Less than 4 characters
    assert len(mock_urlopen_success) == 1
    assert mock_urlopen_success[0]["url"] == SPANISH_WORDLIST_URL
    assert mock_urlopen_success[0]["timeout"] == 5


def test_load_spanish_words_network_failure(mock_urlopen_failure: list[dict[str, Any]]) -> None:
    """Verify the Spanish fallback array is used when the download fails."""
    words = load_spanish_words()

    assert "ordenador" in words
    assert len(words) == 10
    assert len(mock_urlopen_failure) == 1


def test_generate_passphrase_deterministic_selection(
    monkeypatch: pytest.MonkeyPatch,
    mock_secrets_choice: list[Any],
) -> None:
    """Enforce exact cryptographic alignment patterns under static word selections."""
    monkeypatch.setattr("genpass.main.load_portuguese_words", lambda: ["mockedword"])

    passphrase = generate_passphrase(word_count=3, separator=":")

    assert passphrase == "mockedword:mockedword:mockedword"
    assert len(mock_secrets_choice) == 3


def test_generate_password_first_char_constraints(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify absolute structural alignment properties on specified initialization hooks."""
    # Force 'A' for the first choice, then 'b' for remaining loops
    choices = iter(["A", "b", "b", "b", "b"])

    def mock_choice(seq: Any) -> Any:
        return next(choices)

    monkeypatch.setattr("secrets.choice", mock_choice)

    password = generate_password(length=5, special_count=0, first_char_type="uppercase")

    assert password.startswith("A")
    assert len(password) == 5


def test_generate_password_blacklist_enforcement() -> None:
    """Ensure strict ValueError raising path triggers when parameters breach blacklists."""
    with pytest.raises(ValueError, match="Error: The first character .* is blacklisted"):
        _: str = generate_password(length=8, special_count=0, blacklist="X", first_char_type="X")
