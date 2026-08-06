#include <algorithm>
#include <array>
#include <cstdint>
#include <functional>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

using Mask = std::uint64_t;

struct Local {
    std::string name;
    std::array<unsigned, 8> adj{};
    std::array<int, 3> A{};
    std::array<int, 5> U{};
    std::array<int, 3> D{};
    std::array<int, 2> Z{};
};

static std::array<unsigned, 8> decode_graph6(const std::string& s) {
    if (s.empty() || static_cast<unsigned char>(s[0]) - 63 != 8)
        throw std::runtime_error("expected short graph6 of order 8");
    std::vector<int> bits;
    for (std::size_t p = 1; p < s.size(); ++p) {
        int x = static_cast<unsigned char>(s[p]) - 63;
        for (int b = 5; b >= 0; --b) bits.push_back((x >> b) & 1);
    }
    std::array<unsigned, 8> a{};
    int k = 0;
    for (int j = 1; j < 8; ++j) for (int i = 0; i < j; ++i) {
        if (k >= static_cast<int>(bits.size())) throw std::runtime_error("short graph6 payload");
        if (bits[k]) { a[i] |= 1u << j; a[j] |= 1u << i; }
        ++k;
    }
    return a;
}

static bool edge(const std::array<unsigned, 8>& a, int u, int v) {
    return (a[u] >> v) & 1u;
}

static bool bipartite_induced(const std::array<unsigned, 8>& a,
                              const std::array<int, 5>& U) {
    std::array<int, 8> colour;
    colour.fill(-1);
    for (int root : U) if (colour[root] < 0) {
        colour[root] = 0;
        std::vector<int> stack{root};
        while (!stack.empty()) {
            int v = stack.back();
            stack.pop_back();
            for (int w : U) if (edge(a, v, w)) {
                if (colour[w] < 0) {
                    colour[w] = 1 - colour[v];
                    stack.push_back(w);
                } else if (colour[w] == colour[v]) {
                    return false;
                }
            }
        }
    }
    return true;
}

static std::vector<Local> local_decompositions() {
    std::vector<Local> out;
    const std::array<std::string, 2> names{"GEnfbW", "GEjfrw"};
    for (const std::string& name : names) {
        auto a = decode_graph6(name);
        for (int x = 0; x < 8; ++x) for (int y = x + 1; y < 8; ++y)
        for (int z = y + 1; z < 8; ++z) {
            if (edge(a, x, y) || edge(a, x, z) || edge(a, y, z)) continue;
            std::array<int, 3> A{x, y, z};
            std::array<int, 5> U{};
            int ui = 0;
            for (int v = 0; v < 8; ++v) if (v != x && v != y && v != z) U[ui++] = v;
            std::array<int, 3> D{};
            bool ok = true;
            for (int j = 0; j < 3; ++j) {
                std::vector<int> missing;
                for (int u : U) if (!edge(a, A[j], u)) missing.push_back(u);
                if (missing.size() != 1) { ok = false; break; }
                D[j] = missing[0];
            }
            if (!ok || D[0] == D[1] || D[0] == D[2] || D[1] == D[2]) continue;
            if (!bipartite_induced(a, U)) continue;
            std::array<int, 2> Z{};
            int zi = 0;
            for (int u : U) if (u != D[0] && u != D[1] && u != D[2]) Z[zi++] = u;
            if (zi != 2) throw std::runtime_error("bad nondefect set");
            out.push_back(Local{name, a, A, U, D, Z});
        }
    }
    return out;
}

struct Glue {
    int n = 0;
    std::vector<Mask> adj;
    std::vector<int> Ah;
    std::vector<int> Bq;
};

static void add_edge(Glue& g, int u, int v) {
    if (u == v) throw std::runtime_error("loop in glue");
    g.adj[u] |= Mask(1) << v;
    g.adj[v] |= Mask(1) << u;
}

static std::vector<std::vector<int>> permutations_of(std::vector<int> x) {
    std::sort(x.begin(), x.end());
    std::vector<std::vector<int>> out;
    do { out.push_back(x); } while (std::next_permutation(x.begin(), x.end()));
    return out;
}

static Glue build_glue(const Local& L1, int qpos, const Local& L2, int hpos,
                       const std::map<int, int>& mapR,
                       const std::map<int, int>& mapW) {
    // h=0, q=1. Class 1 is I and class 2 is H.
    std::array<int, 8> m1, m2;
    m1.fill(-1); m2.fill(-1);
    std::vector<int> vertex_class{2, 2};
    m1[qpos] = 1;
    int next = 2;
    for (int a : L1.A) { m1[a] = next++; vertex_class.push_back(1); }
    for (int u : L1.U) if (u != qpos) { m1[u] = next++; vertex_class.push_back(2); }
    m2[hpos] = 0;

    std::map<int, int> inverseR, inverseW;
    for (auto [u, v] : mapR) inverseR[v] = u;
    for (auto [u, v] : mapW) inverseW[v] = u;
    for (int a : L2.A) {
        auto it = inverseR.find(a);
        if (it != inverseR.end()) m2[a] = m1[it->second];
        else { m2[a] = next++; vertex_class.push_back(1); }
    }
    for (int u : L2.U) if (u != hpos) {
        auto it = inverseW.find(u);
        if (it != inverseW.end()) m2[u] = m1[it->second];
        else { m2[u] = next++; vertex_class.push_back(2); }
    }

    Glue g;
    g.n = next;
    g.adj.assign(next, 0);
    for (int v = 0; v < 8; ++v) if (v != qpos) add_edge(g, 0, m1[v]);
    for (int v = 0; v < 8; ++v) if (v != hpos) add_edge(g, 1, m2[v]);
    for (int u = 0; u < 8; ++u) for (int v = u + 1; v < 8; ++v) {
        if (u != qpos && v != qpos && edge(L1.adj, u, v)) add_edge(g, m1[u], m1[v]);
        if (u != hpos && v != hpos && edge(L2.adj, u, v)) add_edge(g, m2[u], m2[v]);
    }
    for (int a : L1.A) g.Ah.push_back(m1[a]);
    for (int a : L2.A) g.Bq.push_back(m2[a]);
    for (int u = 0; u < g.n; ++u) if (vertex_class[u] == 1)
    for (int v = u + 1; v < g.n; ++v) if (vertex_class[v] == 1)
        if ((g.adj[u] >> v) & 1ULL) throw std::runtime_error("edge inside I");
    return g;
}

static bool private_colouring(const Glue& g, int u, int v) {
    std::vector<int> remaining;
    Mask remaining_mask = 0, common = 0;
    for (int x = 0; x < g.n; ++x) if (x != u && x != v) {
        remaining.push_back(x);
        remaining_mask |= Mask(1) << x;
        if (((g.adj[u] >> x) & 1ULL) && ((g.adj[v] >> x) & 1ULL))
            common |= Mask(1) << x;
    }
    std::vector<int> colour(g.n, -1);
    std::function<bool(int)> search = [&](int done) {
        unsigned used = 0;
        int left = 0;
        for (int x : remaining) if ((common >> x) & 1ULL) {
            if (colour[x] >= 0) used |= 1u << colour[x];
            else ++left;
        }
        if (__builtin_popcount(used) + left < 4) return false;
        if (done == static_cast<int>(remaining.size())) return __builtin_popcount(used) == 4;

        int best = -1, best_saturation = -1, best_degree = -1;
        unsigned best_forbidden = 0;
        for (int x : remaining) if (colour[x] < 0) {
            unsigned forbidden = 0;
            for (int y : remaining)
                if (colour[y] >= 0 && ((g.adj[x] >> y) & 1ULL))
                    forbidden |= 1u << colour[y];
            int saturation = __builtin_popcount(forbidden);
            int degree = __builtin_popcountll(g.adj[x] & remaining_mask);
            if (saturation > best_saturation ||
                (saturation == best_saturation &&
                 (degree > best_degree ||
                  (degree == best_degree && (best < 0 || x < best))))) {
                best = x;
                best_saturation = saturation;
                best_degree = degree;
                best_forbidden = forbidden;
            }
        }
        for (int c = 0; c < 4; ++c) if (!((best_forbidden >> c) & 1u)) {
            colour[best] = c;
            if (search(done + 1)) return true;
            colour[best] = -1;
        }
        return false;
    };
    return search(0);
}

int main() {
    try {
        auto locals = local_decompositions();
        if (locals.size() != 4) throw std::runtime_error("expected four local decompositions");
        int total = 0, count2 = 0, count3 = 0, survivors = 0;
        std::map<std::tuple<int, std::string, std::string>, int> type_counts;

        for (int r : {2, 3}) for (const Local& L1 : locals) {
            std::vector<int> qpositions;
            if (r == 2) for (int x : L1.D) qpositions.push_back(x);
            else for (int x : L1.Z) qpositions.push_back(x);
            for (int qpos : qpositions) {
                std::vector<int> Rh, Wh;
                for (int a : L1.A) if (edge(L1.adj, a, qpos)) Rh.push_back(a);
                for (int u : L1.U) if (u != qpos && edge(L1.adj, u, qpos)) Wh.push_back(u);
                if (static_cast<int>(Rh.size()) != r) continue;

                for (const Local& L2 : locals) {
                    std::vector<int> hpositions;
                    if (r == 2) for (int x : L2.D) hpositions.push_back(x);
                    else for (int x : L2.Z) hpositions.push_back(x);
                    for (int hpos : hpositions) {
                        std::vector<int> Rq, Wq;
                        for (int a : L2.A) if (edge(L2.adj, a, hpos)) Rq.push_back(a);
                        for (int u : L2.U) if (u != hpos && edge(L2.adj, u, hpos)) Wq.push_back(u);
                        if (static_cast<int>(Rq.size()) != r || Wh.size() != Wq.size() ||
                            r + static_cast<int>(Wh.size()) < 4) continue;

                        for (const auto& pr : permutations_of(Rq))
                        for (const auto& pw : permutations_of(Wq)) {
                            std::map<int, int> mapR, mapW, combined;
                            for (int i = 0; i < r; ++i) {
                                mapR[Rh[i]] = pr[i]; combined[Rh[i]] = pr[i];
                            }
                            for (int i = 0; i < static_cast<int>(Wh.size()); ++i) {
                                mapW[Wh[i]] = pw[i]; combined[Wh[i]] = pw[i];
                            }
                            std::vector<int> intersection = Rh;
                            intersection.insert(intersection.end(), Wh.begin(), Wh.end());
                            bool compatible = true;
                            for (int i = 0; i < static_cast<int>(intersection.size()); ++i)
                            for (int j = i + 1; j < static_cast<int>(intersection.size()); ++j)
                                if (edge(L1.adj, intersection[i], intersection[j]) !=
                                    edge(L2.adj, combined[intersection[i]], combined[intersection[j]]))
                                    compatible = false;
                            if (!compatible) continue;

                            ++total;
                            if (r == 2) ++count2; else ++count3;
                            ++type_counts[{r, L1.name, L2.name}];
                            Glue g = build_glue(L1, qpos, L2, hpos, mapR, mapW);
                            bool good = true;
                            for (int a : g.Ah) if (!private_colouring(g, 0, a)) { good = false; break; }
                            if (good)
                                for (int b : g.Bq) if (!private_colouring(g, 1, b)) { good = false; break; }
                            if (good) ++survivors;
                        }
                    }
                }
            }
        }

        std::cout << "local_decompositions " << locals.size()
                  << "\ncompatible_gluings " << total
                  << "\nintersection_2 " << count2
                  << "\nintersection_3 " << count3
                  << "\nsurvivors " << survivors << "\n";
        if (total != 160 || count2 != 80 || count3 != 80 || survivors != 0)
            throw std::runtime_error("unexpected census");
        std::cout << "status PASS\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "status FAIL: " << ex.what() << "\n";
        return 1;
    }
}
