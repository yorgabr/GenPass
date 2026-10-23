"""Integration tests for passphrase generation (Portuguese, English and Spanish).

Unlike `test_main.py`, nothing inside GenPass is mocked here: `secrets`, the wordlist
parsing/filtering, language routing, the CLI (`main`) and the output streams all run for real.
Only the true system boundaries are replaced, as required by CONTRIBUTING.md:

* the network (`urllib.request.urlopen`) by a URL-aware fake serving realistic wordlists;
* the clipboard (`pyperclip.copy`) and `time.sleep` in the `--clip` scenarios.

Run only this suite with `just test-integration`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, final
from unittest.mock import MagicMock, patch

import pytest

from genpass.main import (
    ENGLISH_FALLBACK_WORDS,
    ENGLISH_WORDLIST_URL,
    PORTUGUESE_BLOCKLIST,
    PORTUGUESE_FALLBACK_WORDS,
    PORTUGUESE_WORDLIST_URL,
    SPANISH_BLOCKLIST,
    SPANISH_FALLBACK_WORDS,
    SPANISH_WORDLIST_URL,
    generate_passphrase,
    main,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import TracebackType

pytestmark = pytest.mark.integration

# Valid entries survive the 4-8 letter, alphabetic-only, lowercase filter of the loader.
PORTUGUESE_VALID = {
    "abacaxi", "janela", "nuvem", "teclado", "codigo", "chave", "sistema", "conexao", "cripto", "senha", "acao",
    "cafezal",
}  # fmt: skip
ENGLISH_VALID = {
    "anchor", "bridge", "candle", "dragon", "engine", "forest", "garden", "hammer", "island", "jungle", "kitten",
    "ladder",
}  # fmt: skip
# Several Spanish entries are accented on purpose: the loader must keep them (str.isalpha) and lowercase them.
SPANISH_VALID = {
    "ventana", "jardín", "canción", "mañana", "árbol", "corazón", "camino", "puente", "montaña", "estrella",
    "ciudad", "viento",
}  # fmt: skip

# Noise the loader must drop: too short, too long, digits, punctuation, profanity and blank lines.
# Uppercase entries must be kept, but lowercased. CRLF endings are used on purpose.
PORTUGUESE_NOISE = ["Sol", "computadores", "Cripto123", "senha-forte", "merda", "PORRA", "", "   "]
ENGLISH_NOISE = ["sun", "extraordinary", "crypto123", "pass-word", "", "   "]
SPANISH_NOISE = ["Sol", "computadoras", "Cripto123", "palabra-clave", "mierda", "PUTA", "", "   "]


def _build_payload(valid: set[str], noise: list[str], *, with_counts: bool = False) -> bytes:
    lines = [w.upper() if i % 3 == 0 else w for i, w in enumerate(sorted(valid))] + noise
    if with_counts:  # frequency-list format ("word count"), as served by the Portuguese and Spanish sources
        lines = [f"{line} {1000 - i}" if line.strip() else line for i, line in enumerate(lines)]
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


PAYLOADS = {
    PORTUGUESE_WORDLIST_URL: _build_payload(PORTUGUESE_VALID, PORTUGUESE_NOISE, with_counts=True),
    ENGLISH_WORDLIST_URL: _build_payload(ENGLISH_VALID, ENGLISH_NOISE),
    SPANISH_WORDLIST_URL: _build_payload(SPANISH_VALID, SPANISH_NOISE, with_counts=True),
}


@dataclass(frozen=True)
class LanguageSpec:
    url: str
    valid: frozenset[str]
    other: frozenset[str]
    fallback: frozenset[str]


LANGUAGES = {
    "pt": LanguageSpec(
        url=PORTUGUESE_WORDLIST_URL,
        valid=frozenset(PORTUGUESE_VALID),
        other=frozenset(ENGLISH_VALID | SPANISH_VALID),
        fallback=frozenset(PORTUGUESE_FALLBACK_WORDS),
    ),
    "en": LanguageSpec(
        url=ENGLISH_WORDLIST_URL,
        valid=frozenset(ENGLISH_VALID),
        other=frozenset(PORTUGUESE_VALID | SPANISH_VALID),
        fallback=frozenset(ENGLISH_FALLBACK_WORDS),
    ),
    "es": LanguageSpec(
        url=SPANISH_WORDLIST_URL,
        valid=frozenset(SPANISH_VALID),
        other=frozenset(PORTUGUESE_VALID | ENGLISH_VALID),
        fallback=frozenset(SPANISH_FALLBACK_WORDS),
    ),
}
LANGUAGE_CODES = tuple(LANGUAGES)


@final
class FakeResponse:
    """Minimal stand-in for the context manager returned by `urllib.request.urlopen`."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def _serve(url: str, timeout: float | None = None) -> FakeResponse:
    _ = timeout  # the call contract (timeout=5) is asserted through the urlopen mock itself
    if url not in PAYLOADS:
        message = f"Unexpected network access to {url!r}"
        raise AssertionError(message)
    return FakeResponse(PAYLOADS[url])


@pytest.fixture
def network() -> Iterator[MagicMock]:
    """Serves each language's wordlist from its own URL; any other URL fails the test."""
    with patch("urllib.request.urlopen", side_effect=_serve) as urlopen:
        yield urlopen


@pytest.fixture
def network_down() -> Iterator[MagicMock]:
    """Simulates a corporate-network/offline failure for every request."""
    with patch("urllib.request.urlopen", side_effect=OSError("Network is unreachable")) as urlopen:
        yield urlopen


@pytest.fixture
def clipboard() -> Iterator[list[str]]:
    """Replaces the system clipboard (recording every copy) and the wipe delay so `--clip` runs instantly."""
    history: list[str] = []
    with patch("genpass.main.pyperclip.copy", side_effect=history.append), patch("genpass.main.time.sleep"):
        yield history


def _words(passphrase: str, separator: str = "-") -> list[str]:
    return passphrase.split(separator)


# --------------------------------------------------------------------------------------
# generate_passphrase: wordlist download -> filtering -> secure selection -> join
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("language", LANGUAGE_CODES)
def test_passphrase_uses_only_filtered_words_of_the_requested_language(network: MagicMock, language: str) -> None:
    spec = LANGUAGES[language]

    passphrase = generate_passphrase(word_count=8, separator="-", language=language)

    words = _words(passphrase)
    assert len(words) == 8
    assert set(words) <= spec.valid
    assert not set(words) & spec.other
    network.assert_called_once_with(spec.url, timeout=5)


@pytest.mark.parametrize("language", LANGUAGE_CODES)
def test_passphrase_filter_drops_noise_and_lowercases(network: MagicMock, language: str) -> None:
    spec = LANGUAGES[language]

    # 400 draws from 12 words make it practically impossible to miss a valid word.
    words = set(_words(generate_passphrase(word_count=400, separator=" ", language=language), " "))

    assert words == spec.valid
    assert all(w == w.lower() and w.isalpha() and 4 <= len(w) <= 8 for w in words)
    assert network.call_count == 1


def test_passphrase_defaults_to_portuguese(network: MagicMock) -> None:
    passphrase = generate_passphrase()

    words = _words(passphrase)
    assert len(words) == 4
    assert set(words) <= PORTUGUESE_VALID
    network.assert_called_once_with(PORTUGUESE_WORDLIST_URL, timeout=5)


@pytest.mark.parametrize("language", LANGUAGE_CODES)
@pytest.mark.parametrize("separator", [".", "_", " ", "::"])
def test_passphrase_honours_word_count_and_separator(network: MagicMock, language: str, separator: str) -> None:
    passphrase = generate_passphrase(word_count=5, separator=separator, language=language)

    assert passphrase.count(separator) == 4
    assert set(_words(passphrase, separator)) <= LANGUAGES[language].valid
    assert network.call_count == 1


@pytest.mark.parametrize("language", LANGUAGE_CODES)
def test_passphrase_is_not_deterministic(network: MagicMock, language: str) -> None:
    results = {generate_passphrase(word_count=4, language=language) for _ in range(50)}

    assert len(results) > 1
    assert network.call_count == 50


def test_passphrase_rejects_unsupported_language_before_touching_the_network(network: MagicMock) -> None:
    with pytest.raises(ValueError, match="Unsupported language 'fr'"):
        _ = generate_passphrase(language="fr")

    network.assert_not_called()


# --------------------------------------------------------------------------------------
# Fallback behaviour when the download fails or yields nothing usable
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("language", LANGUAGE_CODES)
def test_passphrase_falls_back_to_builtin_words_when_network_is_down(
    network_down: MagicMock,
    capsys: pytest.CaptureFixture[str],
    language: str,
) -> None:
    passphrase = generate_passphrase(word_count=6, language=language)

    captured = capsys.readouterr()
    assert set(_words(passphrase)) <= LANGUAGES[language].fallback
    assert captured.out == ""
    assert "Falling back to integrated dictionary" in captured.err
    assert "Network is unreachable" in captured.err
    network_down.assert_called_once_with(LANGUAGES[language].url, timeout=5)


@pytest.mark.parametrize("language", LANGUAGE_CODES)
def test_passphrase_falls_back_when_wordlist_has_no_valid_entries(
    capsys: pytest.CaptureFixture[str],
    language: str,
) -> None:
    useless_payload = b"\r\nab\r\n12345\r\nthis-is-not-a-word\r\n"

    with patch("urllib.request.urlopen", return_value=FakeResponse(useless_payload)):
        passphrase = generate_passphrase(word_count=6, language=language)

    assert set(_words(passphrase)) <= LANGUAGES[language].fallback
    assert "Downloaded wordlist was empty" in capsys.readouterr().err


def test_fallback_wordlists_do_not_share_words() -> None:
    portuguese = set(PORTUGUESE_FALLBACK_WORDS)
    english = set(ENGLISH_FALLBACK_WORDS)
    spanish = set(SPANISH_FALLBACK_WORDS)

    assert not portuguese & english
    assert not portuguese & spanish
    assert not english & spanish


# --------------------------------------------------------------------------------------
# CLI end to end: argparse -> generate_passphrase -> stdout/stderr/clipboard
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("language", LANGUAGE_CODES)
def test_cli_prints_passphrase_to_stdout(network: MagicMock, capsys: pytest.CaptureFixture[str], language: str) -> None:
    main(["--passphrase", "--lang", language, "--words", "5", "--sep", "_"])

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    words = _words(captured.out.strip(), "_")
    assert len(words) == 5
    assert set(words) <= LANGUAGES[language].valid
    network.assert_called_once_with(LANGUAGES[language].url, timeout=5)


def test_cli_defaults_to_portuguese_four_words_dash_separated(
    network: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["-p"])

    words = _words(capsys.readouterr().out.strip())
    assert len(words) == 4
    assert set(words) <= PORTUGUESE_VALID
    network.assert_called_once_with(PORTUGUESE_WORDLIST_URL, timeout=5)


@pytest.mark.parametrize("language", LANGUAGE_CODES)
def test_cli_keeps_stdout_clean_when_falling_back(
    network_down: MagicMock,
    capsys: pytest.CaptureFixture[str],
    language: str,
) -> None:
    main(["-p", "--lang", language, "-w", "3"])

    captured = capsys.readouterr()
    # The warning must go to stderr, so `genpass -p | clip` never receives it.
    assert set(_words(captured.out.strip())) <= LANGUAGES[language].fallback
    assert len(_words(captured.out.strip())) == 3
    assert "Warning" in captured.err
    assert "Warning" not in captured.out
    network_down.assert_called_once()


def test_cli_rejects_unknown_language(network: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["-p", "--lang", "fr"])

    assert excinfo.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
    network.assert_not_called()


@pytest.mark.parametrize("language", LANGUAGE_CODES)
def test_cli_clip_copies_passphrase_then_wipes_without_printing_it(
    network: MagicMock,
    clipboard: list[str],
    capsys: pytest.CaptureFixture[str],
    language: str,
) -> None:
    main(["-p", "--lang", language, "--words", "4", "--clip"])

    assert len(clipboard) == 2
    copied, wiped = clipboard
    assert len(_words(copied)) == 4
    assert set(_words(copied)) <= LANGUAGES[language].valid
    assert wiped == ""
    out = capsys.readouterr().out
    assert copied not in out
    assert "copied to clipboard" in out
    assert "Clipboard wiped clean" in out
    network.assert_called_once()


def test_wordlist_download_refuses_non_https_urls(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("genpass.main.PORTUGUESE_WORDLIST_URL", "file:///etc/passwd")

    with patch("urllib.request.urlopen") as urlopen:
        passphrase = generate_passphrase(word_count=4, language="pt")

    assert set(_words(passphrase)) <= LANGUAGES["pt"].fallback
    assert "non-HTTPS" in capsys.readouterr().err
    urlopen.assert_not_called()


def test_portuguese_blocklist_removes_profanity_from_the_wordlist(network: MagicMock) -> None:
    assert {"merda", "porra"} <= PORTUGUESE_BLOCKLIST

    words = set(_words(generate_passphrase(word_count=400, separator="-", language="pt")))

    assert not words & PORTUGUESE_BLOCKLIST
    assert words == PORTUGUESE_VALID
    network.assert_called_once()


def test_spanish_blocklist_removes_profanity_from_the_wordlist(network: MagicMock) -> None:
    assert {"mierda", "puta"} <= SPANISH_BLOCKLIST

    words = set(_words(generate_passphrase(word_count=400, separator="-", language="es")))

    assert not words & SPANISH_BLOCKLIST
    assert words == SPANISH_VALID
    network.assert_called_once()


def test_portuguese_wordlist_only_reads_the_top_lines(monkeypatch: pytest.MonkeyPatch, network: MagicMock) -> None:
    monkeypatch.setattr("genpass.main.PORTUGUESE_WORDLIST_MAX_LINES", 3)

    words = set(_words(generate_passphrase(word_count=200, separator="-", language="pt")))

    assert words == {"abacaxi", "acao", "cafezal"}  # first three lines of the (sorted) payload
    network.assert_called_once()


def test_spanish_wordlist_only_reads_the_top_lines(monkeypatch: pytest.MonkeyPatch, network: MagicMock) -> None:
    monkeypatch.setattr("genpass.main.SPANISH_WORDLIST_MAX_LINES", 3)

    words = set(_words(generate_passphrase(word_count=200, separator="-", language="es")))

    # First three lines of the sorted payload: sorted() puts accented letters after plain ASCII ones.
    assert words == set(sorted(SPANISH_VALID)[:3])
    network.assert_called_once()


def test_portuguese_blocklist_does_not_overlap_the_fallback_words() -> None:
    assert not PORTUGUESE_BLOCKLIST & set(PORTUGUESE_FALLBACK_WORDS)


def test_spanish_blocklist_does_not_overlap_the_fallback_words() -> None:
    assert not SPANISH_BLOCKLIST & set(SPANISH_FALLBACK_WORDS)
