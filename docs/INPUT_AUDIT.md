# Provenance and exact audit of Rybin's triangle counterexample

The instance in `instances/Rybin_triangle.json` is attributed to Dmitry Rybin,
who announced it publicly on 22 July 2026:

- X announcement: <https://x.com/DmitryRybin1/status/2079904005652893709>
- Shared GPT-5.6 Pro transcript:
  <https://chatgpt.com/share/6a60b2eb-0b64-83ee-9c76-7931ca1de063>

This repository reproduces the instance for independent exact verification and
does not claim authorship of it. The instance was treated as an untrusted
candidate source: the verifier reconstructs every source-terminal path solely
from the arc list rather than trusting a declared path decomposition or the
announcement's conclusion.

The independent verifier establishes:

- the DAG has exactly two source-terminal paths for each of three terminals;
- there are exactly eight unsplittable routings;
- the unique zero-cost primary choices have capacity-good selection system
  `{empty, each singleton}`, i.e. the stable sets of `K3`;
- the fractional cost is exactly `58`;
- every additive-`D` capacity-good routing costs at least `60`.

Rybin's triangle is the immediate methodological and historical antecedent of
the article. It shows that additive-D load bounds can make three zero-cost
detours behave as the stable sets of `K3`. The article explicitly reframes its
universal construction as a generalisation of that mechanism. The universal
proof does not depend on trusting the announcement, because the triangle and the
new construction are checked separately.

The public announcement is not a conventional peer-reviewed publication.
Nevertheless, the exact finite certificate directly refutes the cost-preserving
conjecture as formulated: its fractional cost is `58`, while every
additive-`15`-good unsplittable routing costs at least `60`.
