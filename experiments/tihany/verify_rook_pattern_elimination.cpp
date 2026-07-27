#include <array>
#include <cstdint>
#include <iostream>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

using Edge = std::pair<int,int>;

static Edge ordered(int a, int b) {
    return a < b ? Edge{a,b} : Edge{b,a};
}

static const std::set<Edge> BASE = {
    {0,1},{0,2},{0,3},{0,4},{0,5},{0,6},{0,7},{0,8},
    {1,2},{1,3},{1,5},{1,7},{1,9},{1,10},{1,11},{1,12},
    {2,5},{2,6},{2,7},{2,12},
    {3,6},{3,7},{3,8},{3,9},{3,11},
    {4,5},{4,6},{4,7},{4,8},
    {5,8},{5,11},{5,12},
    {6,8},{7,10},
    {9,10},{9,11},{9,12},{10,11},{10,12}
};

static const std::array<Edge,12> CROSS = {{
    {4,9},{4,10},{4,11},{4,12},
    {6,9},{6,10},{6,11},{6,12},
    {8,9},{8,10},{8,11},{8,12}
}};

static std::set<Edge> interface_graph(int pattern) {
    std::uint32_t mask = 0;
    if (pattern == 0) mask = 0;
    else if (pattern == 2) mask = 16;
    else if (pattern == 3) mask = 17;
    else if (pattern == 4) mask = 64;
    else if (pattern == 6) mask = 128;
    else throw std::runtime_error("unsupported pattern");

    auto edges = BASE;
    for (int bit = 0; bit < 12; ++bit) {
        if ((mask >> bit) & 1u) edges.insert(CROSS[bit]);
    }
    return edges;
}

static bool has_edge(const std::set<Edge>& edges, int a, int b) {
    return edges.count(ordered(a,b)) != 0;
}

static int degree(const std::set<Edge>& edges, int v) {
    int d = 0;
    for (auto [a,b] : edges) d += (a == v || b == v);
    return d;
}

static std::vector<int> common_inside_interface(
    const std::set<Edge>& edges,
    int a,
    int b
) {
    std::vector<int> result;
    for (int w = 0; w < 13; ++w) {
        if (w != a && w != b && has_edge(edges,a,w) && has_edge(edges,b,w)) {
            result.push_back(w);
        }
    }
    return result;
}

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        for (int pattern : {0,2,3,4,6}) {
            const auto edges = interface_graph(pattern);
            require(degree(edges,0) == 8, "wrong degree at centre 0");
            require(degree(edges,1) == 9, "wrong degree at centre 1");
            require(has_edge(edges,4,6), "edge 4-6 missing");
            require(has_edge(edges,4,8), "edge 4-8 missing");
            require(has_edge(edges,6,8), "edge 6-8 missing");

            if (pattern == 0) {
                require(
                    degree(edges,4) == 5 && degree(edges,6) == 5 && degree(edges,8) == 5,
                    "wrong degree-five triangle in pattern 0"
                );
            } else {
                require(degree(edges,8) == 5, "wrong degree at vertex 8");
                require(degree(edges,4) <= 6, "vertex 4 has excessive interface degree");
                require(has_edge(edges,5,12), "edge 5-12 missing");
                require(
                    common_inside_interface(edges,5,12) == std::vector<int>({1,2}),
                    "wrong fixed common neighbourhood of edge 5-12"
                );
                require(
                    has_edge(edges,0,4) && has_edge(edges,0,8) && has_edge(edges,4,8),
                    "triangle 0,4,8 missing"
                );
                require(
                    has_edge(edges,0,1) && has_edge(edges,0,2) && has_edge(edges,1,2),
                    "triangle 0,1,2 missing"
                );
                require(
                    has_edge(edges,1,2) && has_edge(edges,1,12) && has_edge(edges,2,12),
                    "triangle 1,2,12 missing"
                );
            }
            std::cout << "pattern " << pattern << " checked\n";
        }
        std::cout << "status PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "status FAIL: " << error.what() << "\n";
        return 1;
    }
}
