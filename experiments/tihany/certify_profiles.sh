#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 PROFILE_ROOT CERTIFICATE_ROOT" >&2
  exit 2
fi

ROOT=$(realpath "$1")
CERT=$2
mkdir -p "$CERT"
CERT=$(realpath "$CERT")
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

expected=35
found=0
certified=0
: > "$CERT/manifest.tsv"

for dir in "$ROOT"/*; do
  [[ -d "$dir" ]] || continue
  profile=$(basename "$dir")
  cnf="$dir/static.cnf"
  result="$dir/result.json"
  [[ -f "$result" ]] || continue
  found=$((found+1))
  status=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$result")
  if [[ "$status" != unsat ]]; then
    echo "profile $profile is not UNSAT: $status" >&2
    exit 1
  fi
  [[ -f "$cnf" ]] || { echo "missing $cnf" >&2; exit 1; }
  out="$CERT/$profile"
  bash "$SCRIPT_DIR/run_certified.sh" "$cnf" "$out"
  printf '%s\t%s\t%s\t%s\n' \
    "$profile" \
    "$(sha256sum "$cnf" | cut -d' ' -f1)" \
    "$(cat "$out/proof.drat.sha256" | cut -d' ' -f1)" \
    "$(cat "$out/drat-trim.commit")" >> "$CERT/manifest.tsv"
  certified=$((certified+1))
done

if [[ $found -ne $expected || $certified -ne $expected ]]; then
  echo "expected $expected profiles, found=$found certified=$certified" >&2
  exit 1
fi

sha256sum "$CERT/manifest.tsv" | tee "$CERT/manifest.sha256"
echo "ALL 35 ATTACHMENT PROFILES CERTIFIED UNSAT"
