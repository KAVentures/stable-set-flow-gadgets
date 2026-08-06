# Audit of the earlier order-17 exploratory scripts

The earlier uploaded files are useful exploratory work, but they do not support the previously stated claim that a clean direct core CNF had already been solved to UNSAT.

## `order17_rigid_base.py`

The file is not the requested core encoding. In addition to the order-17 reduction, it imposes:

- `delta(H) >= 5`;
- covering of `H` by the four attachments;
- a fixed omission-size tuple supplied on the command line;
- `K5`-freeness;
- at least four common neighbours on every edge;
- cross-domination;
- internal-edge escape projections;
- isolation projections for every `I-H` incidence;
- local 3-colourability of every completed neighbourhood.

Most importantly, the driver contains

```python
for it in range(1):
```

so it performs only one solver call. The CEGAR branches that add 4-/5-colouring cuts or activate failed deletion blocks cannot be iterated by that version.

## `order17_5554_pattern_scan.py`

This is an accelerated scan restricted to the omission profile `(5,5,5,4)`. It shares the auxiliary structural encoding above and is not a direct encoding of the defining graph problem.

## Consequence

The earlier scripts and their exploratory summaries may guide theorem discovery, but they are not used as evidence for core UNSAT. The fresh `core_search.py` starts again from the defining graph problem and preserves every generated colouring cut before emitting a static DIMACS formula.