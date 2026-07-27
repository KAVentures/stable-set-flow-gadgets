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
  git clone --depth 1 --branch rel-2.1.3 https://github.com/arminbiere/cadical.git "$TOOLS/cadical"
fi
(
  cd "$TOOLS/cadical"
  git rev-parse HEAD | tee "$OUT/cadical.commit"
  ./configure
  make -j"$(nproc)"
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
  make -j"$(nproc)"
)

set +e
"$TOOLS/cadical/build/cadical" "$CNF" "$OUT/proof.drat" 2>&1 | tee "$OUT/cadical.log"
CADICAL_STATUS=${PIPESTATUS[0]}
set -e
if [[ $CADICAL_STATUS -ne 20 ]]; then
  echo "CaDiCaL did not return UNSAT (exit 20); status=$CADICAL_STATUS" >&2
  exit 1
fi

sha256sum "$OUT/proof.drat" | tee "$OUT/proof.drat.sha256"
"$TOOLS/drat-trim/drat-trim" "$CNF" "$OUT/proof.drat" -t 40000 -L "$OUT/proof.lrat" 2>&1 | tee "$OUT/drat-trim.log"
sha256sum "$OUT/proof.lrat" | tee "$OUT/proof.lrat.sha256"

if [[ -x "$TOOLS/drat-trim/lrat-check" ]]; then
  "$TOOLS/drat-trim/lrat-check" "$CNF" "$OUT/proof.lrat" 2>&1 | tee "$OUT/lrat-check.log"
fi

echo "CERTIFIED UNSAT"
