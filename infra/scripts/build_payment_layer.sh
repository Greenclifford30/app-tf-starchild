#!/usr/bin/env bash
# Rebuild the versioned dependency artifact when changing requirements-payments.txt.
set -euo pipefail
cd "$(dirname "$0")/.."
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT
python3 -m pip install --no-compile --target "$build_dir/python" --platform manylinux2014_aarch64 --implementation cp --python-version 3.13 --only-binary=:all: -r requirements-payments.txt
python3 scripts/package_payment_dependencies.py "$build_dir/python" artifacts/stripe-python-3.13-arm64.zip
