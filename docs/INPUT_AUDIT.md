# Audit of the supplied DGG investigation

The supplied investigation was treated as an untrusted candidate source. Its final
triangle instance was reconstructed solely from the arc list, not from its declared
path decomposition.

The independent verifier establishes:

- the DAG has exactly two source-terminal paths for each of three terminals;
- there are exactly eight unsplittable routings;
- the unique zero-cost primary choices have capacity-good selection system
  `{empty, each singleton}`, i.e. the stable sets of `K3`;
- the fractional cost is exactly `58`;
- every additive-`D` capacity-good routing costs at least `60`.

The universal realisation and odd-cycle theorems in the paper do not depend on the
triangle's claimed literature priority. The triangle was used as a methodological
seed: it showed that mandatory baseline load can create an incompatibility not
captured by ordinary path intersection, while the earlier failed constructions
identified borrowed-prefix closure as the central adversarial issue.
