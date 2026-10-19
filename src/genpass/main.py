import argparse
import secrets
import string
import sys
import time
import urllib.request

import pyperclip

# Subtitle-based frequency list ("word count" per line, most frequent first).
# Only the top lines are used: they are the common, memorable words (like the English list).
PORTUGUESE_WORDLIST_URL = (
    "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/pt_br/pt_br_50k.txt"
)
PORTUGUESE_WORDLIST_MAX_LINES = 10_000
# Subtitle vocabulary includes profanity, so it is filtered out (the English list is "no-swears").
PORTUGUESE_BLOCKLIST = frozenset(
    {
        "babaca",
        "babacas",
        "bicha",
        "bichona",
        "boceta",
        "bosta",
        "buceta",
        "bunda",
        "cacete",
        "canalha",
        "caralho",
        "carilha",
        "cu",
        "cuzão",
        "esporro",
        "estupro",
        "estuprou",
        "foda",
        "fode",
        "fodendo",
        "foder",
        "fodeu",
        "fodido",
        "fudendo",
        "fuder",
        "fudeu",
        "fudi",
        "fudido",
        "fudo",
        "imbecil",
        "imbecis",
        "merda",
        "merdas",
        "piranha",
        "piroca",
        "porra",
        "porrada",
        "puta",
        "putas",
        "puto",
        "pênis",
        "sacana",
        "tesão",
        "vadia",
        "vadias",
        "vagina",
        "viado",
    }
)
ENGLISH_WORDLIST_URL = (
    "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt"
)
SUPPORTED_LANGUAGES = ("pt", "en")

PORTUGUESE_FALLBACK_WORDS = [
    "computador",
    "seguranca",
    "chave",
    "sistema",
    "cripto",
    "conexao",
    "janela",
    "nuvem",
    "teclado",
    "codigo",
]
ENGLISH_FALLBACK_WORDS = [
    "computer",
    "security",
    "key",
    "system",
    "crypto",
    "network",
    "window",
    "cloud",
    "keyboard",
    "code",
]


def _fetch_words(
    url: str,
    fallback: list[str],
    *,
    max_lines: int | None = None,
    exclude: frozenset[str] = frozenset(),
) -> list[str]:
    """Fetches a clean word list from `url`, returning a copy of `fallback` on any failure.

    Accepts one word per line, optionally followed by other columns (e.g. a frequency count).
    Only the first `max_lines` lines are read; words in `exclude` are dropped.
    """
    try:
        if not url.startswith("https://"):
            raise ValueError(f"Refusing to download a wordlist over a non-HTTPS URL: {url!r}")
        with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310 - https-only, enforced above
            raw_text = response.read().decode("utf-8")
        candidates = (line.split()[0].lower() for line in raw_text.splitlines()[:max_lines] if line.strip())
        words = list(
            dict.fromkeys(w for w in candidates if w.isalpha() and 4 <= len(w) <= 8 and w not in exclude),
        )
        if not words:
            raise ValueError("Downloaded wordlist was empty.")
    except Exception as e:
        print(f"[!] Warning: Falling back to integrated dictionary matrix ({e}).", file=sys.stderr)
        return list(fallback)
    return words


def load_portuguese_words() -> list[str]:
    """Fetches a clean list of Portuguese words safely for passphrase generation."""
    return _fetch_words(
        PORTUGUESE_WORDLIST_URL,
        PORTUGUESE_FALLBACK_WORDS,
        max_lines=PORTUGUESE_WORDLIST_MAX_LINES,
        exclude=PORTUGUESE_BLOCKLIST,
    )


def load_english_words() -> list[str]:
    """Fetches a clean list of English words safely for passphrase generation."""
    return _fetch_words(ENGLISH_WORDLIST_URL, ENGLISH_FALLBACK_WORDS)


def load_words(language: str) -> list[str]:
    """Dispatches to the language loader (looked up at call time, so loaders stay patchable)."""
    if language == "pt":
        return load_portuguese_words()
    if language == "en":
        return load_english_words()
    raise ValueError(f"Error: Unsupported language '{language}'. Choose one of: {', '.join(SUPPORTED_LANGUAGES)}.")


def generate_passphrase(word_count: int = 4, separator: str = "-", language: str = "pt") -> str:
    """Generates an exceptionally strong, memorable passphrase using cryptographically secure choices."""
    wordlist = load_words(language)
    chosen_words = [secrets.choice(wordlist) for _ in range(word_count)]
    return separator.join(chosen_words)


def generate_password(
    length: int = 8,
    special_count: int = 0,
    blacklist: str = ":/\\|\"'`",
    first_char_type: str = "alnum",
) -> str:
    """Generates customized string tokens adhering strictly to structural constraints."""

    def filter_blacklist(characters: str) -> str:
        return "".join(c for c in characters if c not in blacklist)

    digits = filter_blacklist(string.digits)
    uppercase = filter_blacklist(string.ascii_uppercase)
    lowercase = filter_blacklist(string.ascii_lowercase)
    alphabetic = uppercase + lowercase
    alnum = alphabetic + digits
    all_specials = filter_blacklist("".join(c for c in string.punctuation if c not in string.whitespace))
    all_valid_chars = alnum + all_specials

    if special_count > 0 and not all_specials:
        raise ValueError("Error: The blacklist removed all available special characters.")

    if first_char_type == "alnum":
        first_char_pool = alnum
    elif first_char_type == "alphabetic":
        first_char_pool = alphabetic
    elif first_char_type == "uppercase":
        first_char_pool = uppercase
    elif first_char_type == "lowercase":
        first_char_pool = lowercase
    elif first_char_type == "numeric":
        first_char_pool = digits
    elif first_char_type == "symbolic":
        first_char_pool = all_specials
    elif first_char_type == "any":
        first_char_pool = all_valid_chars
    elif len(first_char_type) == 1:
        if first_char_type in blacklist:
            raise ValueError(f"Error: The first character '{first_char_type}' is blacklisted.")
        first_char_pool = first_char_type
    else:
        raise ValueError(f"Invalid first character type: '{first_char_type}'")

    if not first_char_pool:
        raise ValueError("Error: No characters available for the first character after applying the blacklist.")

    first_char = secrets.choice(first_char_pool)
    remaining_length = length - 1
    if remaining_length < 0:
        raise ValueError("Error: Password length must be at least 1 character.")

    is_first_char_symbol = first_char in all_specials
    special_adjustment = 1 if (is_first_char_symbol and special_count > 0) else 0
    remaining_specials = max(0, special_count - special_adjustment)

    if remaining_specials > remaining_length:
        raise ValueError(f"Error: Special character count ({special_count}) exceeds available password length.")

    password_body = [secrets.choice(all_specials) for _ in range(remaining_specials)]
    if not alnum:
        raise ValueError("Error: No alphanumeric characters available after applying the blacklist.")

    remaining_slots = remaining_length - len(password_body)
    password_body.extend(secrets.choice(alnum) for _ in range(remaining_slots))

    secrets.SystemRandom().shuffle(password_body)
    return first_char + "".join(password_body)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Unified Strong Password & Passphrase Generator Utility.")
    parser.add_argument("-l", "--length", type=int, default=8, help="Password length")
    parser.add_argument("-s", "--specials", type=int, default=0, help="Number of special characters")
    parser.add_argument("-b", "--blacklist", type=str, default=":/\\|\"'`", help="Forbidden ASCII characters")
    parser.add_argument("-f", "--first", type=str, default="alnum", help="First character type selection")
    parser.add_argument("-c", "--clip", action="store_true", help="Clipboard autofade mode")
    parser.add_argument("-p", "--passphrase", action="store_true", help="Generate word passphrase")
    parser.add_argument("-w", "--words", type=int, default=4, help="Number of passphrase words")
    parser.add_argument("--sep", type=str, default="-", help="Passphrase word separator")
    parser.add_argument(
        "--lang",
        type=str,
        default="pt",
        choices=SUPPORTED_LANGUAGES,
        help="Passphrase wordlist language",
    )

    args = parser.parse_args(argv)

    try:
        if args.passphrase:
            secret_out = generate_passphrase(word_count=args.words, separator=args.sep, language=args.lang)
        else:
            secret_out = generate_password(
                length=args.length,
                special_count=args.specials,
                blacklist=args.blacklist,
                first_char_type=args.first,
            )

        if args.clip:
            pyperclip.copy(secret_out)
            print("[+] Secret copied to clipboard successfully!")
            time.sleep(1)
            pyperclip.copy("")
            print("[✓] Clipboard wiped clean.")
        else:
            print(f"{secret_out}")
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
