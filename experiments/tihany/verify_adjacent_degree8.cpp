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

using Mask = std::uint32_t;

static std::array<unsigned, 8> decode_graph6(const std::string& s) {
    if (s.empty() || int(static_cast<unsigned char>(s[0])) - 63 != 8)
        throw std::runtime_error("expected short graph6 of order eight");
    std::vector<int> bits;
    for (std::size_t p = 1; p < s.size(); ++p) {
        int x = int(static_cast<unsigned char>(s[p])) - 63;
        for (int k = 5; k >= 0; --k) bits.push_back((x >> k) & 1);
    }
    std::array<unsigned, 8> adj{};
    int k = 0;
    for (int j = 1; j < 8; ++j) for (int i = 0; i < j; ++i) {
        if (k >= static_cast<int>(bits.size())) throw std::runtime_error("short graph6 payload");
        if (bits[k++]) {
            adj[i] |= 1u << j;
            adj[j] |= 1u << i;
        }
    }
    return adj;
}

static bool edge(const std::array<unsigned, 8>& adj, int u, int v) {
    return (adj[u] >> v) & 1u;
}

struct Glue {
    int n;
    std::vector<Mask> adj;
    std::vector<int> n_h;
    std::vector<int> n_q;
};

static void add_edge(Glue& g, int u, int v) {
    if (u == v) throw std::runtime_error("loop in local amalgam");
    g.adj[u] |= Mask(1) << v;
    g.adj[v] |= Mask(1) << u;
}

static Glue build_glue(
    const std::array<unsigned, 8>& first,
    int q_position,
    const std::array<unsigned, 8>& second,
    int h_position,
    const std::map<int, int>& common_map
) {
    // Global centres are h=0 and q=1.  The first graph is G[N(h)] and
    // q_position represents q.  The second is G[N(q)] and h_position represents h.
    std::array<int, 8> map_first, map_second;
    map_first.fill(-1);
    map_second.fill(-1);
    map_first[q_position] = 1;
    int next = 2;
    for (int v = 0; v < 8; ++v)
        if (v != q_position) map_first[v] = next++;

    std::map<int, int> inverse;
    for (auto [u, v] : common_map) inverse[v] = u;
    map_second[h_position] = 0;
    for (int v = 0; v < 8; ++v) {
        if (v == h_position) continue;
        auto it = inverse.find(v);
        if (it != inverse.end()) map_second[v] = map_first[it->second];
        else map_second[v] = next++;
    }

    Glue g{next, std::vector<Mask>(next, 0), {}, {}};
    for (int v = 0; v < 8; ++v) {
        add_edge(g, 0, map_first[v]);
        g.n_h.push_back(map_first[v]);
    }
    for (int v = 0; v < 8; ++v) {
        add_edge(g, 1, map_second[v]);
        g.n_q.push_back(map_second[v]);
    }
    for (int u = 0; u < 8; ++u) for (int v = u + 1; v < 8; ++v) {
        if (edge(first, u, v)) add_edge(g, map_first[u], map_first[v]);
        if (edge(second, u, v)) add_edge(g, map_second[u], map_second[v]);
    }
    return g;
}

static bool has_common_rainbow_four_colouring(const Glue& g, int u, int v) {
    Mask full = (Mask(1) << g.n) - 1;
    Mask remaining = full & ~(Mask(1) << u) & ~(Mask(1) << v);
    Mask common = g.adj[u] & g.adj[v] & remaining;
    std::vector<int> colour(g.n, -1);

    std::function<bool(Mask)> search = [&](Mask left) {
        unsigned used_on_common = 0;
        int uncoloured_common = 0;
        for (Mask z = common; z; z &= z - 1) {
            int x = __builtin_ctz(z);
            if (colour[x] < 0) ++uncoloured_common;
            else used_on_common |= 1u << colour[x];
        }
        if (__builtin_popcount(used_on_common) + uncoloured_common < 4) return false;
        if (!left) return __builtin_popcount(used_on_common) == 4;

        int best = -1, best_saturation = -1, best_degree = -1;
        unsigned best_forbidden = 0;
        for (Mask z = left; z; z &= z - 1) {
            int x = __builtin_ctz(z);
            unsigned forbidden = 0;
            Mask already_coloured_neighbours = g.adj[x] & remaining & ~left;
            for (Mask y = already_coloured_neighbours; y; y &= y - 1) {
                int w = __builtin_ctz(y);
                if (colour[w] >= 0) forbidden |= 1u << colour[w];
            }
            int saturation = __builtin_popcount(forbidden);
            int degree = __builtin_popcount(g.adj[x] & remaining);
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
        for (int c = 0; c < 4; ++c) {
            if ((best_forbidden >> c) & 1u) continue;
            colour[best] = c;
            if (search(left & ~(Mask(1) << best))) return true;
            colour[best] = -1;
        }
        return false;
    };
    return search(remaining);
}

static std::vector<std::vector<int>> all_permutations(std::vector<int> values) {
    std::sort(values.begin(), values.end());
    std::vector<std::vector<int>> out;
    do out.push_back(values); while (std::next_permutation(values.begin(), values.end()));
    return out;
}

int main() {
    try {
        const std::array<std::string, 2> names{"GEnfbW", "GEjfrw"};
        const std::array<std::array<unsigned, 8>, 2> local{
            decode_graph6(names[0]), decode_graph6(names[1])
        };

        int total = 0, survivors = 0;
        std::map<std::tuple<std::string, int, std::string, int>, std::array<int, 2>> counts;

        for (int first_type = 0; first_type < 2; ++first_type) {
            for (int q_position = 0; q_position < 8; ++q_position) {
                std::vector<int> first_common;
                for (int x = 0; x < 8; ++x)
                    if (edge(local[first_type], q_position, x)) first_common.push_back(x);

                for (int second_type = 0; second_type < 2; ++second_type) {
                    for (int h_position = 0; h_position < 8; ++h_position) {
                        std::vector<int> second_common;
                        for (int x = 0; x < 8; ++x)
                            if (edge(local[second_type], h_position, x)) second_common.push_back(x);
                        if (first_common.size() != second_common.size()) continue;

                        for (const auto& permutation : all_permutations(second_common)) {
                            bool compatible = true;
                            for (std::size_t a = 0; a < first_common.size(); ++a)
                                for (std::size_t b = a + 1; b < first_common.size(); ++b)
                                    if (edge(local[first_type], first_common[a], first_common[b]) !=
                                        edge(local[second_type], permutation[a], permutation[b]))
                                        compatible = false;
                            if (!compatible) continue;

                            std::map<int, int> common_map;
                            for (std::size_t a = 0; a < first_common.size(); ++a)
                                common_map[first_common[a]] = permutation[a];
                            Glue g = build_glue(
                                local[first_type], q_position,
                                local[second_type], h_position,
                                common_map
                            );

                            ++total;
                            auto key = std::make_tuple(
                                names[first_type], int(first_common.size()),
                                names[second_type], int(second_common.size())
                            );
                            ++counts[key][0];

                            bool good = true;
                            for (int x : g.n_h) {
                                if (!has_common_rainbow_four_colouring(g, 0, x)) {
                                    good = false;
                                    break;
                                }
                            }
                            if (good) {
                                for (int x : g.n_q) {
                                    if (!has_common_rainbow_four_colouring(g, 1, x)) {
                                        good = false;
                                        break;
                                    }
                                }
                            }
                            if (good) {
                                ++survivors;
                                ++counts[key][1];
                            }
                        }
                    }
                }
            }
        }

        std::cout << "compatible_gluings " << total << "\n";
        for (const auto& [key, value] : counts) {
            std::cout << "type "
                      << std::get<0>(key) << " " << std::get<1>(key) << " "
                      << std::get<2>(key) << " " << std::get<3>(key)
                      << " total " << value[0] << " survive " << value[1] << "\n";
        }
        std::cout << "survivors " << survivors << "\n";
        if (total != 184 || survivors != 0)
            throw std::runtime_error("unexpected adjacent-degree-eight census");
        std::cout << "status PASS\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "status FAIL: " << ex.what() << "\n";
        return 1;
    }
}
