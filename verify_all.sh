#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python3 verification/verify_triangle.py instances/Rybin_triangle.json
python3 verification/verify_c5.py instances/C5.json
python3 verification/verify_symbolic.py --max-k 200
python3 verification/test_mutations.py
