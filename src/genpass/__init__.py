"""GenPass: An Enterprise-Grade Cryptographically Secure Token and Passphrase Generator."""

import importlib.metadata

FALLBACK_VERSION = "0.1.0-dev"
FALLBACK_AUTHOR = "Yorga Babuscan <yorgabr@gmail.com>"
FALLBACK_DESCRIPTION = "Unified Cryptographically Secure Strong Password & Passphrase Generator"

try:
    _metadata = importlib.metadata.metadata("genpass")
    __version__ = _metadata.get("Version", FALLBACK_VERSION)
    __author__ = _metadata.get("Author-email", FALLBACK_AUTHOR)
    __description__ = _metadata.get("Description", FALLBACK_DESCRIPTION)
except importlib.metadata.PackageNotFoundError:
    # Fallback pattern when executed locally outside an installation framework
    __version__ = FALLBACK_VERSION
    __author__ = FALLBACK_AUTHOR
    __description__ = FALLBACK_DESCRIPTION

