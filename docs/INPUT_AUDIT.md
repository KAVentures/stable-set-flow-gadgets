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

The announcement URL was resolved directly through X's public oEmbed service on
27 July 2026. The nearby status `2080022912199766400` is a later reply about
brute-force search, not the 58/60 announcement.

The independent verifier establishes:

- the DAG has exactly two source-terminal paths for each of three terminals;
- there are exactly eight unsplittable routings;
- the unique zero-cost primary choices have capacity-good selection system
  `{empty, each singleton}`, i.e. the stable sets of `K3`;
- the fractional cost is exactly `58`;
- every additive-`D` capacity-good routing costs at least `60`.
- the underlying undirected graph is a subdivision of `K4`, and hence planar.

Rybin's triangle is the immediate methodological and historical antecedent of
the article. It shows that additive-D load bounds can make three zero-cost
detours behave as the stable sets of `K3`. The article explicitly reframes its
universal construction as a generalisation of that mechanism. The universal
proof does not depend on trusting the announcement, because the triangle and the
new construction are checked separately.

The mathematical conclusion does not depend on treating the public announcement
as a publication or authority. It follows from the reproduced finite data and
the independent exact audit: the fractional cost is `58`, while every
additive-`15`-good unsplittable routing costs at least `60`.
