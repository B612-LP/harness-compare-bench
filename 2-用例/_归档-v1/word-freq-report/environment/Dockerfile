FROM ubuntu:24.04
WORKDIR /app

# Task input (fixed, deterministic). The corpus contains deliberate ties:
# 'a' / 'dog' / 'tests' all have count 5, and the top-5 boundary falls inside
# that tie group, so ASCII tie-break (a < dog < tests) decides whether 'dog'
# or 'tests' makes the report. Digit tokens (2026, 3rd) must be dropped.
COPY corpus.txt /app/corpus.txt
