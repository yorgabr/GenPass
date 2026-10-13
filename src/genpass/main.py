import argparse
import secrets
import string
import sys
import time
import urllib.request
import pyperclip

PORTUGUESE_WORDLIST_URL = "https://githubusercontent.com"

def load_portuguese_words() -> list[str]:
    """Fetches a clean list of Portuguese words safely for passphrase generation."""
    try:
        with urllib.request.urlopen(PORTUGUESE_WORDLIST_URL, timeout=5) as response:
            raw_text = response.read().decode('utf-8')
            words = [
                w.strip().lower() for w in raw_text.splitlines() 
                if w.strip().isalpha() and 4 <= len(w.strip()) <= 8
            ]
            if not words:
                raise ValueError("Downloaded wordlist was empty.")
            return words
    except Exception as e:
        print(f"[!] Warning: Falling back to integrated dictionary matrix ({e}).", file=sys.stderr)
        return ["computador", "seguranca", "chave", "sistema", "cripto", "conexao", "janela", "nuvem", "teclado", "codigo"]

def generate_passphrase(word_count: int = 4, separator: str = "-") -> str:
    """Generates an exceptionally strong, memorable passphrase using cryptographically secure choices."""
    wordlist = load_portuguese_words()
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

def main() -> None:
    parser = argparse.ArgumentParser(description="Unified Strong Password & Passphrase Generator Utility.")
    parser.add_argument("-l", "--length", type=int, default=8, help="Password length")
    parser.add_argument("-s", "--specials", type=int, default=0, help="Number of special characters")
    parser.add_argument("-b", "--blacklist", type=str, default=":/\\|\"'`", help="Forbidden ASCII characters")
    parser.add_argument("-f", "--first", type=str, default="alnum", help="First character type selection")
    parser.add_argument("-c", "--clip", action="store_true", help="Clipboard autofade mode")
    parser.add_argument("-p", "--passphrase", action="store_true", help="Generate word passphrase")
    parser.add_argument("-w", "--words", type=int, default=4, help="Number of passphrase words")
    parser.add_argument("--sep", type=str, default="-", help="Passphrase word separator")

    args = parser.parse_args()

    try:
        if args.passphrase:
            secret_out = generate_passphrase(word_count=args.words, separator=args.sep)
        else:
            secret_out = generate_password(
                length=args.length, special_count=args.specials, blacklist=args.blacklist, first_char_type=args.first
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
