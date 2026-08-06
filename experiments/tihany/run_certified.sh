#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 FORMULA.cnf OUTPUT_DIR" >&2
  exit 2
fi

CNF=$(realpath "$1")
OUT=$2
mkdir -p "$OUT" "$OUT/tools"
OUT=$(realpath "$OUT")
TOOLS="$OUT/tools"

sha256sum "$CNF" | tee "$OUT/formula.sha256"

if [[ ! -d "$TOOLS/cadical/.git" ]]; then
  git clone --depth 1 --branch rel-2.1.3 \
    https://github.com/arminbiere/cadical.git "$TOOLS/cadical"
fi
(
  cd "$TOOLS/cadical"
  test "$(git rev-parse --abbrev-ref HEAD)" = "rel-2.1.3" || true
  git rev-parse HEAD | tee "$OUT/cadical.commit"
  ./configure
  make -j"$(nproc)"
  ./build/cadical --version | tee "$OUT/cadical.version"
)

DRAT_TRIM_COMMIT=effa1dcce85c878236f8313133dff1a2b766cd7c
if [[ ! -d "$TOOLS/drat-trim/.git" ]]; then
  git clone https://github.com/marijnheule/drat-trim.git "$TOOLS/drat-trim"
fi
(
  cd "$TOOLS/drat-trim"
  git fetch --depth 1 origin "$DRAT_TRIM_COMMIT"
  git checkout --detach "$DRAT_TRIM_COMMIT"
  test "$(git rev-parse HEAD)" = "$DRAT_TRIM_COMMIT"
  git rev-parse HEAD | tee "$OUT/drat-trim.commit"
  make clean >/dev/null 2>&1 || true
  make -j"$(nproc)"
  test -x ./drat-trim
  test -x ./lrat-check
)

set +e
"$TOOLS/cadical/build/cadical" --no-binary \
  "$CNF" "$OUT/proof.drat" 2>&1 | tee "$OUT/cadical.log"
CADICAL_STATUS=${PIPESTATUS[0]}
set -e
if [[ $CADICAL_STATUS -ne 20 ]]; then
  echo "CaDiCaL did not return UNSAT (exit 20); status=$CADICAL_STATUS" >&2
  exit 1
fi

test -s "$OUT/proof.drat"
sha256sum "$OUT/proof.drat" | tee "$OUT/proof.drat.sha256"

# First checker: validate the original DRAT proof and independently generate LRAT.
"$TOOLS/drat-trim/drat-trim" \
  "$CNF" "$OUT/proof.drat" \
  -t 40000 -L "$OUT/proof.lrat" 2>&1 | tee "$OUT/drat-trim.log"
test -s "$OUT/proof.lrat"
sha256sum "$OUT/proof.lrat" | tee "$OUT/proof.lrat.sha256"

# Second checker: a separately implemented linear-time LRAT verifier.
"$TOOLS/drat-trim/lrat-check" \
  "$CNF" "$OUT/proof.lrat" 2>&1 | tee "$OUT/lrat-check.log"

cat > "$OUT/certificate-manifest.txt" <<EOF
status=CERTIFIED_UNSAT
formula_sha256=$(cut -d' ' -f1 "$OUT/formula.sha256")
proof_drat_sha256=$(cut -d' ' -f1 "$OUT/proof.drat.sha256")
proof_lrat_sha256=$(cut -d' ' -f1 "$OUT/proof.lrat.sha256")
cadical_commit=$(cat "$OUT/cadical.commit")
drat_trim_commit=$(cat "$OUT/drat-trim.commit")
EOF
sha256sum "$OUT/certificate-manifest.txt" | tee "$OUT/certificate-manifest.sha256"

echo "CERTIFIED UNSAT: DRAT and LRAT checks both passed"
