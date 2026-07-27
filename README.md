# Stable-Set Flow Gadgets

[![Verification](https://github.com/KAVentures/stable-set-flow-gadgets/actions/workflows/verify.yml/badge.svg)](https://github.com/KAVentures/stable-set-flow-gadgets/actions/workflows/verify.yml)

Reproducibility repository for:

> Koyar Afrasyab, *From Rybin's Triangle Counterexample to Universal
> Independence-System Realisations in Unsplittable Flow* (2026).

This research note generalises the stable-set mechanism in Dmitry Rybin's
seven-vertex counterexample to Goemans' cost-preserving unsplittable-flow
conjecture. It proves that every finite loopless independence system can be
strongly realised by an acyclic single-source unsplittable-flow gadget. It also
gives a uniform odd-cycle family with an exact cost-preserving
additive-congestion threshold and an exhaustive rational certificate for `C5`.

## Relationship to Rybin's counterexample

The triangle instance in this repository is **not an original construction of
this project**. It reproduces the counterexample publicly announced by Dmitry
Rybin on 22 July 2026:

- [X announcement](https://x.com/DmitryRybin1/status/2079904005652893709)
- [Shared GPT-5.6 Pro transcript](https://chatgpt.com/share/6a60b2eb-0b64-83ee-9c76-7931ca1de063)

The repository independently derives all paths and checks all eight routings,
confirming fractional cost `58` and minimum additive-`15`-good integral cost
`60`. The article is framed as a generalisation of that mechanism, not as the
source of the triangle construction. The announcement is not yet a conventional
peer-reviewed publication, but the exact finite certificate refutes the
cost-preserving conjecture as stated.

## Results

- Universal realisation of every finite loopless independence system.
- Stable-set realisation for every finite simple graph.
- A uniform `C_(2k+1)` family violating the odd-cycle inequality.
- Exact threshold `tau = 1 - bq`.
- Exhaustive verification of all `3^10 = 59,049` routings of the `C5`
  certificate.

## Repository layout

```text
.
├── paper/
│   ├── article.pdf
│   ├── article.tex
│   ├── article.docx
│   ├── references.bib
│   └── figures/c5.png
├── instances/
│   ├── C5.json
│   └── Rybin_triangle.json
├── verification/
│   ├── verify_c5.py
│   ├── verify_symbolic.py
│   ├── verify_triangle.py
│   └── test_mutations.py
├── docs/
├── generate_cycle.py
└── verify_all.sh
```

## Reproduce the results

Requirements:

- Python 3.9 or newer
- No third-party Python packages

Run the complete verification suite:

```bash
./verify_all.sh
```

The suite:

1. independently audits Rybin's provenance-labelled triangle instance;
2. derives every path and enumerates all 59,049 routings of the exact `C5`
   certificate;
3. checks the symbolic odd-cycle identities for `k=1,...,200`; and
4. confirms that four adversarially mutated certificates are rejected.

Individual checks:

```bash
python3 verification/verify_c5.py instances/C5.json
python3 verification/verify_symbolic.py --max-k 200
python3 verification/verify_triangle.py instances/Rybin_triangle.json
python3 verification/test_mutations.py
```

Generate another odd-cycle instance:

```bash
python3 generate_cycle.py 3 -o instances/C7.json
```

## Build the paper

From the `paper` directory:

```bash
pdflatex -interaction=nonstopmode -halt-on-error article.tex
pdflatex -interaction=nonstopmode -halt-on-error article.tex
```

The committed PDF is provided for convenient reading. arXiv submissions should
use the TeX source and figure rather than the generated PDF.

## Citation

GitHub exposes the repository citation through [`CITATION.cff`](CITATION.cff).
Until an archival DOI is assigned, cite the paper using the metadata in that
file.

## Licenses

- Code, verification scripts, and machine-readable instances: MIT License
  (`LICENSE-CODE`).
- Paper, figures, and documentation: Creative Commons Attribution 4.0
  International (`LICENSE-PAPER`).
- Rybin's reproduced triangle instance carries an explicit provenance exception;
  see `NOTICE` and `docs/INPUT_AUDIT.md`.

## Contact

Koyar Afrasyab — [koyar@kinvectum.com](mailto:koyar@kinvectum.com)
