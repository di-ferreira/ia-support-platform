#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"

echo "Seeding Appwrite..."
uv run python ../scripts/seed_appwrite.py
echo "Done."
