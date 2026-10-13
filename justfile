default:
    @just --list

# Dynamic evaluation macros parsing the Master Single Source of Truth
VERSION := `uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"`
AUTHOR_NAME  := `uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['authors'][0]['name'])"`
AUTHOR_EMAIL := `uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['authors'][0]['email'])"`

# Run ruff formatter check, linter engine, and security-centric basedpyright static analysis
check:
    uv run ruff format --check src/ tests/
    uv run ruff check src/ tests/
    uv run basedpyright src/ tests/

# Execute suite using extreme isolation unit mocking infrastructure
test:
    uv run pytest -v --tb=short tests/

# Execute system installation into your local environment profile path cleanly via uv
install:
    uv tool install --force .

# Automated SemVer bumper path
bump target:
    @echo "[*] Current version identified as: {{VERSION}}"
    uv run python -c " \
    import sys; \
    parts = '{{VERSION}}'.split('.'); \
    idx = {'major': 0, 'minor': 1, 'patch': 2}['{{target}}']; \
    parts[idx] = str(int(parts[idx]) + 1); \
    if idx < 2: parts[idx+1:] = ['0'] * (2 - idx); \
    new_v = '.'.join(parts); \
    content = open('pyproject.toml', 'r').read(); \
    updated = content.replace('version = \"{{VERSION}}\"', f'version = \"{new_v}\"'); \
    open('pyproject.toml', 'w').write(updated); \
    print(f'[+] Successfully bumped pyproject.toml to: {new_v}')"

# Build standard distribution targets and synthesize package distribution manifestations
package:
    uv build
    @echo "[+] Compiling package targets for v{{VERSION}} by {{AUTHOR_NAME}} ({{AUTHOR_EMAIL}})..."
    
    # Injecting the single-source-of-truth metadata into the Scoop Manifest JSON structure
    @echo '{\n  "version": "{{VERSION}}",\n  "description": "Unified Password Generator",\n  "homepage": "https://github.com",\n  "notes": "Maintained by {{AUTHOR_NAME}} <{{AUTHOR_EMAIL}}>"\n}' > dist/genpass.json
    @echo "    -> [Scoop] Synhesized dist/genpass.json with integrated author metadata."
    
    # Injecting the master reference attributes inside the Homebrew Ruby formula metadata strings
    @echo 'class Genpass < Formula\n  desc "Unified Password Generator by {{AUTHOR_NAME}}"\n  homepage "https://github.com"\n  url "https://github.com/archive/refs/tags/v{{VERSION}}.tar.gz"\n  version "{{VERSION}}"\nend' > dist/genpass.rb
    @echo "    -> [Homebrew] Synthesized dist/genpass.rb with integrated formula descriptions."
