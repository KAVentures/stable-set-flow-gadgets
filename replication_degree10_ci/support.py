from __future__ import annotations

import itertools

FREE = 2
NEG, POS, NONE = 0, 1, 2


def cover_restr(B):
    return tuple(FREE if b == NONE else (0 if b == POS else 1) for b in B)


def cover_weight(enc, B):
    return sum(enc.w[i] if b == POS else enc.tau - enc.w[i]
               for i, b in enumerate(B) if b != NONE)


def intersection(B, p):
    return sum(1 for i, b in enumerate(B)
               if (b == POS and ((p >> i) & 1))
               or (b == NEG and not ((p >> i) & 1)))


def mismatch_row(row, p):
    return [row[j] if ((p >> j) & 1) == 0 else -row[j]
            for j in range(len(row))]


def forbid(enc, variables, bits):
    enc.add_clause([v if bit == 0 else -v
                    for v, bit in zip(variables, bits)])


def add_xor(enc, a, b):
    z = enc.new_var()
    enc.add_clause([-z, a, b])
    enc.add_clause([-z, -a, -b])
    enc.add_clause([z, -a, b])
    enc.add_clause([z, a, -b])
    return z


def strict_lex_chain(enc, rows):
    for r in range(len(rows) - 1):
        enc.add_lex_geq(rows[r], rows[r + 1])
        differences = [add_xor(enc, a, b)
                       for a, b in zip(rows[r], rows[r + 1])]
        enc.add_clause(differences)


def exact_count(enc, variables, target):
    for bits in itertools.product((0, 1), repeat=len(variables)):
        if sum(bits) != target:
            forbid(enc, variables, bits)


def allowed_count(enc, variables, lo, hi):
    for bits in itertools.product((0, 1), repeat=len(variables)):
        if not (lo <= sum(bits) <= hi):
            forbid(enc, variables, bits)


def add_single_decrement_residual_holes(enc):
    """Necessary conditions from entrywise minimality of a gap-one witness."""
    start_v, start_c = enc.var_count, enc.clause_count
    witnesses = 0
    for target in range(enc.d):
        for residual_target_bit in (1, 0):
            witnesses += 1
            packing = [[enc.new_var() for _ in range(enc.d)]
                       for _ in range(enc.tau - 1)]
            residual = [enc.new_var() for _ in range(enc.d)]
            enc.add_clause([residual[target]
                            if residual_target_bit else -residual[target]])
            for row in packing:
                for p in range(1 << enc.d):
                    enc.add_clause([enc.x[p]] + mismatch_row(row, p))
            for p in range(1 << enc.d):
                enc.add_clause([-enc.x[p]] + mismatch_row(residual, p))
            for j in range(enc.d):
                exact_count(enc,
                            [row[j] for row in packing] + [residual[j]],
                            enc.w[j])
            for r in range(len(packing) - 1):
                enc.add_lex_geq(packing[r], packing[r + 1])
    return {
        "witnesses": witnesses,
        "variables": enc.var_count - start_v,
        "clauses": enc.clause_count - start_c,
    }


def add_pair_decrement_hierarchy(enc):
    """Encode every packing forced by decrementing one complementary pair.

    If a units are removed from capacity i and b units from capacity bar(i),
    q=a+b with 1 <= q < tau, then the pair cover has weight tau-q. Every cover
    loses at most q, hence the new covering number is exactly tau-q. Entrywise
    minimality of the original violating weight forces a packing of tau-q sets.
    """
    start_v, start_c = enc.var_count, enc.clause_count
    witnesses = rows_total = 0
    for target in range(enc.d):
        positive = enc.w[target]
        negative = enc.tau - positive
        for dec_pos in range(positive + 1):
            for dec_neg in range(negative + 1):
                q = dec_pos + dec_neg
                if q == 0 or q >= enc.tau:
                    continue
                packing_size = enc.tau - q
                witnesses += 1
                rows_total += packing_size
                rows = [[enc.new_var() for _ in range(enc.d)]
                        for _ in range(packing_size)]
                for row in rows:
                    for p in range(1 << enc.d):
                        enc.add_clause([enc.x[p]] + mismatch_row(row, p))
                for j in range(enc.d):
                    column = [row[j] for row in rows]
                    if j == target:
                        exact_count(enc, column, positive - dec_pos)
                    else:
                        lo = max(0, enc.w[j] - q)
                        hi = min(packing_size, enc.w[j])
                        allowed_count(enc, column, lo, hi)
                for r in range(len(rows) - 1):
                    enc.add_lex_geq(rows[r], rows[r + 1])
    return {
        "witnesses": witnesses,
        "rows": rows_total,
        "variables": enc.var_count - start_v,
        "clauses": enc.clause_count - start_c,
    }


def add_support(enc, support_size):
    """Encode a basic optimal fractional packing support.

    Support points are distinct feasible cube points. Since every positive
    coefficient is strictly below one, coordinate j occurs in at least w_j+1
    support rows and its complement in at least tau-w_j+1 rows. Minimum covers
    intersect every support row exactly once. A mate of a positive-support row
    cannot itself be minimum, hence has integer weight at least tau+1.
    """
    start_v, start_c = enc.var_count, enc.clause_count
    rows = [[enc.new_var() for _ in range(enc.d)]
            for _ in range(support_size)]
    for row in rows:
        for p in range(1 << enc.d):
            enc.add_clause([enc.x[p]] + mismatch_row(row, p))
    for j in range(enc.d):
        low = enc.w[j] + 1
        high = support_size - (enc.tau - enc.w[j] + 1)
        if low > high:
            enc.add_clause([])
            continue
        column = [row[j] for row in rows]
        for bits in itertools.product((0, 1), repeat=support_size):
            if not (low <= sum(bits) <= high):
                forbid(enc, column, bits)
    strict_lex_chain(enc, rows)

    mate_candidates = []
    for B in itertools.product((NEG, POS, NONE), repeat=enc.d):
        weight = cover_weight(enc, B)
        size = sum(b != NONE for b in B)
        if enc.tau + 1 <= weight <= size + enc.tau - 2:
            mate_candidates.append((B, weight, -enc.y[cover_restr(B)]))
    for row in rows:
        for p in range(1 << enc.d):
            candidates = [cover_literal
                          for B, weight, cover_literal in mate_candidates
                          if weight <= intersection(B, p) + enc.tau - 2]
            enc.add_clause(mismatch_row(row, p) + candidates)

    max_cover_size = support_size - enc.tau
    minimum_covers = []
    for B in itertools.product((NEG, POS, NONE), repeat=enc.d):
        if cover_weight(enc, B) != enc.tau:
            continue
        size = sum(b != NONE for b in B)
        restriction_var = enc.y[cover_restr(B)]
        if size > max_cover_size:
            enc.add_clause([restriction_var])
        else:
            minimum_covers.append((B, restriction_var))
    for B, restriction_var in minimum_covers:
        used = [i for i, b in enumerate(B) if b != NONE]
        for row in rows:
            for bits in itertools.product((0, 1), repeat=len(used)):
                hits = sum(1 for i, bit in zip(used, bits)
                           if (B[i] == POS and bit)
                           or (B[i] == NEG and not bit))
                if hits != 1:
                    clause = [restriction_var]
                    clause.extend(row[i] if bit == 0 else -row[i]
                                  for i, bit in zip(used, bits))
                    enc.add_clause(clause)
    return {
        "size": support_size,
        "rows": rows,
        "mate_candidates": len(mate_candidates),
        "minimum_cover_patterns": len(minimum_covers),
        "variables": enc.var_count - start_v,
        "clauses": enc.clause_count - start_c,
    }
