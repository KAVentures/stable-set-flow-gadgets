#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Mask = std::uint32_t;

struct Graph { int n; std::vector<Mask> adj; };

Graph read_graph(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open graph file");
    int n; in >> n;
    if (n <= 0 || n > 30) throw std::runtime_error("unsupported order");
    Graph g{n, std::vector<Mask>(n, 0)};
    int u, v;
    while (in >> u >> v) {
        if (!(0 <= u && u < v && v < n)) throw std::runtime_error("bad edge");
        if ((g.adj[u] >> v) & 1U) throw std::runtime_error("duplicate edge");
        g.adj[u] |= Mask(1) << v; g.adj[v] |= Mask(1) << u;
    }
    return g;
}

int popcount(Mask x) { return __builtin_popcount(x); }

bool colour_static_rec(const Graph& g, const std::vector<int>& order, int pos, int k, std::vector<int>& col) {
    if (pos == static_cast<int>(order.size())) return true;
    int v = order[pos]; unsigned forbidden = 0;
    for (int i = 0; i < pos; ++i) {
        int w = order[i];
        if ((g.adj[v] >> w) & 1U) forbidden |= 1U << col[w];
    }
    for (int c = 0; c < k; ++c) {
        if ((forbidden >> c) & 1U) continue;
        col[v] = c;
        if (colour_static_rec(g, order, pos + 1, k, col)) return true;
        col[v] = -1;
    }
    return false;
}

bool kcolourable_static(const Graph& g, Mask vertices, int k) {
    std::vector<int> order;
    for (int v = 0; v < g.n; ++v) if ((vertices >> v) & 1U) order.push_back(v);
    std::sort(order.begin(), order.end(), [&](int a, int b) {
        int da = popcount(g.adj[a] & vertices), db = popcount(g.adj[b] & vertices);
        return da != db ? da > db : a < b;
    });
    std::vector<int> col(g.n, -1);
    return colour_static_rec(g, order, 0, k, col);
}

int choose_dsatur(const Graph& g, Mask uncoloured, Mask vertices, const std::vector<int>& col) {
    int best = -1, best_sat = -1, best_deg = -1;
    for (int v = 0; v < g.n; ++v) {
        if (!((uncoloured >> v) & 1U)) continue;
        unsigned seen = 0;
        for (int w = 0; w < g.n; ++w)
            if (((g.adj[v] >> w) & 1U) && col[w] >= 0) seen |= 1U << col[w];
        int sat = popcount(seen), deg = popcount(g.adj[v] & vertices);
        if (sat > best_sat || (sat == best_sat && (deg > best_deg || (deg == best_deg && (best < 0 || v < best))))) {
            best = v; best_sat = sat; best_deg = deg;
        }
    }
    return best;
}

bool colour_dsatur_rec(const Graph& g, Mask vertices, Mask uncoloured, int k, int used, std::vector<int>& col) {
    if (!uncoloured) return true;
    int v = choose_dsatur(g, uncoloured, vertices, col); unsigned forbidden = 0;
    for (int w = 0; w < g.n; ++w)
        if (((g.adj[v] >> w) & 1U) && col[w] >= 0) forbidden |= 1U << col[w];
    int limit = std::min(k, used + 1);
    for (int c = 0; c < limit; ++c) {
        if ((forbidden >> c) & 1U) continue;
        col[v] = c;
        if (colour_dsatur_rec(g, vertices, uncoloured & ~(Mask(1) << v), k, std::max(used, c + 1), col)) return true;
        col[v] = -1;
    }
    return false;
}

bool kcolourable_dsatur(const Graph& g, Mask vertices, int k) {
    std::vector<int> col(g.n, -1);
    return colour_dsatur_rec(g, vertices, vertices, k, 0, col);
}

int alpha_rec(const Graph& g, Mask candidates, int size, int& best) {
    if (size + popcount(candidates) <= best) return best;
    if (!candidates) { best = std::max(best, size); return best; }
    int v = -1, max_deg = -1;
    for (int x = 0; x < g.n; ++x) if ((candidates >> x) & 1U) {
        int d = popcount(g.adj[x] & candidates);
        if (d > max_deg) { max_deg = d; v = x; }
    }
    alpha_rec(g, candidates & ~g.adj[v] & ~(Mask(1) << v), size + 1, best);
    alpha_rec(g, candidates & ~(Mask(1) << v), size, best);
    return best;
}

int independence_number(const Graph& g) {
    int best = 0; Mask full = (Mask(1) << g.n) - 1U;
    return alpha_rec(g, full, 0, best);
}

bool connected(const Graph& g) {
    Mask seen = 1U, frontier = 1U;
    while (frontier) {
        Mask bit = frontier & (~frontier + 1U); frontier ^= bit;
        int v = __builtin_ctz(bit); Mask add = g.adj[v] & ~seen;
        seen |= add; frontier |= add;
    }
    return popcount(seen) == g.n;
}

int main(int argc, char** argv) {
    try {
        if (argc < 2 || argc > 4) {
            std::cerr << "usage: verify_graph_generic graph.edges [expected_order] [minimum_degree]\n";
            return 2;
        }
        int expected_order = argc >= 3 ? std::stoi(argv[2]) : 17;
        int degree_bound = argc >= 4 ? std::stoi(argv[3]) : 8;
        Graph g = read_graph(argv[1]);
        if (g.n != expected_order) throw std::runtime_error("unexpected order");
        Mask full = (Mask(1) << g.n) - 1U;
        if (!connected(g)) throw std::runtime_error("disconnected graph");
        bool complete = true; int edges = 0, delta = g.n;
        for (int v = 0; v < g.n; ++v) {
            if ((g.adj[v] >> v) & 1U) throw std::runtime_error("loop");
            delta = std::min(delta, popcount(g.adj[v]));
        }
        for (int u = 0; u < g.n; ++u) for (int v = u + 1; v < g.n; ++v) {
            if ((g.adj[u] >> v) & 1U) ++edges; else complete = false;
        }
        if (complete) throw std::runtime_error("complete graph");
        if (delta < degree_bound) throw std::runtime_error("minimum degree below bound");
        if (kcolourable_static(g, full, 5) || kcolourable_dsatur(g, full, 5))
            throw std::runtime_error("graph is 5-colourable");
        if (!kcolourable_static(g, full, 6) || !kcolourable_dsatur(g, full, 6))
            throw std::runtime_error("graph is not verified 6-colourable");
        for (int u = 0; u < g.n; ++u) for (int v = u + 1; v < g.n; ++v) {
            if (!((g.adj[u] >> v) & 1U)) continue;
            Mask rem = full & ~(Mask(1) << u) & ~(Mask(1) << v);
            if (!kcolourable_static(g, rem, 4) || !kcolourable_dsatur(g, rem, 4))
                throw std::runtime_error("an edge deletion is not 4-colourable");
            if (kcolourable_dsatur(g, rem, 3)) throw std::runtime_error("an edge deletion is 3-colourable");
        }
        std::cout << "VERIFIED GENERIC n=" << g.n << " m=" << edges
                  << " alpha=" << independence_number(g) << " delta=" << delta
                  << " chi=6 deletion_chi=4\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "VERIFICATION FAILED: " << ex.what() << "\n";
        return 1;
    }
}
