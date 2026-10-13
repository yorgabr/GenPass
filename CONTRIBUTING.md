# Contributing Guidelines

Thank you for allocating your processing time to improve the `genpass` utility codebase. Please review this reference framework before opening a pull request.

## Table of Contents
1. [Code Quality Infrastructure](#code-quality-infrastructure)
2. [Development Environment Setup](#development-environment-setup)
3. [Extreme Mock Verification Testing Standards](#extreme-mock-verification-testing-standards)
4. [Pull Request Validation Steps](#pull-request-validation-steps)

## Code Quality Infrastructure
The repository maintains strict checking policies to enforce consistent style paradigms and prevent security anti-patterns:
- **Linter & Formatter Framework:** Orchestrated via `ruff`.
- **Static Typing & Static Analysis:** Managed using `basedpyright` configuration matrices.

## Development Environment Setup
We utilize `uv` and `just` to optimize developer lifecycle management tasks:
```bash
# Execute localized static validation suites across source domains
just check

# Trigger unit test validation routines
just test
```

## Extreme Mock Verification Testing Standards
Every functional component addition requires a matching suite containing isolated boundary test structures. Direct database, system clipboard, or socket calls must be mocked via `unittest.mock` configurations to ensure unit performance remains independent of peripheral state conditions.

## Pull Request Validation Steps
1. Fork the canonical codebase repository on GitHub.com.
2. Formulate your enhancements inside an independent tracking branch context.
3. Validate all localized tasks locally using `just check` and `just test`.
4. Ensure documentation matrices are expanded to match updated feature capabilities.
