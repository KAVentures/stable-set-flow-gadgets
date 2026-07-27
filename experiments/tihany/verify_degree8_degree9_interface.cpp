#include <algorithm>
#include <array>
#include <cstdint>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using U64 = std::uint64_t;
using Mask = std::uint16_t;

struct Graph {
    int n=0;
    std::array<Mask,14> adj{};
};

static int popcount(unsigned x) {
    return __builtin_popcount(x);
}

static bool edge(const Graph& g,int u,int v) {
    return ((g.adj[u]>>v)&1u)!=0;
}

static void add_edge(Graph& g,int u,int v) {
    g.adj[u]|=Mask(1u<<v);
    g.adj[v]|=Mask(1u<<u);
}

static Graph decode_mask(int n,U64 mask) {
    Graph g;
    g.n=n;
    int bit=0;
    for(int i=0;i<n;++i) for(int j=i+1;j<n;++j,++bit) {
        if((mask>>bit)&1u) add_edge(g,i,j);
    }
    return g;
}

static U64 encode_order(const Graph& g,const std::vector<int>& order) {
    U64 mask=0;
    int bit=0;
    for(int i=0;i<g.n;++i) for(int j=i+1;j<g.n;++j,++bit) {
        if(edge(g,order[i],order[j])) mask|=U64(1)<<bit;
    }
    return mask;
}

static U64 canonical_small(const Graph& g) {
    std::vector<int> colour(g.n);
    for(int v=0;v<g.n;++v) colour[v]=popcount(g.adj[v]);
    while(true) {
        std::vector<std::vector<int>> signature(g.n);
        for(int v=0;v<g.n;++v) {
            signature[v].push_back(colour[v]);
            std::vector<int> neighbours;
            for(int w=0;w<g.n;++w) if(edge(g,v,w)) {
                neighbours.push_back(colour[w]);
            }
            std::sort(neighbours.begin(),neighbours.end());
            signature[v].insert(
                signature[v].end(),neighbours.begin(),neighbours.end()
            );
        }
        auto values=signature;
        std::sort(values.begin(),values.end());
        values.erase(std::unique(values.begin(),values.end()),values.end());
        std::vector<int> next(g.n);
        for(int v=0;v<g.n;++v) {
            next[v]=int(
                std::lower_bound(values.begin(),values.end(),signature[v])-values.begin()
            );
        }
        if(next==colour) break;
        colour.swap(next);
    }

    std::map<int,std::vector<int>> cells_by_colour;
    for(int v=0;v<g.n;++v) cells_by_colour[colour[v]].push_back(v);
    std::vector<std::vector<int>> cells;
    for(auto& [c,cell]:cells_by_colour) cells.push_back(cell);

    U64 best=~U64(0);
    std::vector<int> order;
    std::function<void(int)> search=[&](int ci) {
        if(ci==int(cells.size())) {
            best=std::min(best,encode_order(g,order));
            return;
        }
        auto cell=cells[ci];
        std::sort(cell.begin(),cell.end());
        do {
            order.insert(order.end(),cell.begin(),cell.end());
            search(ci+1);
            order.resize(order.size()-cell.size());
        } while(std::next_permutation(cell.begin(),cell.end()));
    };
    search(0);
    return best;
}

static bool k_colourable(const Graph& g,Mask vertices,int k) {
    std::array<int,14> colour;
    colour.fill(-1);
    const int total=popcount(vertices);
    std::function<bool(int)> search=[&](int done) {
        if(done==total) return true;
        int best=-1,best_sat=-1,best_deg=-1;
        unsigned best_forbidden=0;
        for(int v=0;v<g.n;++v) if(((vertices>>v)&1u)&&colour[v]<0) {
            unsigned forbidden=0;
            for(int w=0;w<g.n;++w) if(colour[w]>=0&&edge(g,v,w)) {
                forbidden|=1u<<colour[w];
            }
            int sat=popcount(forbidden);
            int deg=popcount(g.adj[v]&vertices);
            if(sat>best_sat || (sat==best_sat&&deg>best_deg) ||
               (sat==best_sat&&deg==best_deg&&(best<0||v<best))) {
                best=v;
                best_sat=sat;
                best_deg=deg;
                best_forbidden=forbidden;
            }
        }
        for(int c=0;c<k;++c) if(((best_forbidden>>c)&1u)==0) {
            colour[best]=c;
            if(search(done+1)) return true;
            colour[best]=-1;
        }
        return false;
    };
    return search(0);
}

static bool has_clique(const Graph& g,int r) {
    for(unsigned subset=0;subset<(1u<<g.n);++subset) if(popcount(subset)==r) {
        bool ok=true;
        for(int v=0;v<g.n&&ok;++v) if((subset>>v)&1u) {
            unsigned others=subset&~(1u<<v);
            if((others&~g.adj[v])!=0) ok=false;
        }
        if(ok) return true;
    }
    return false;
}

static bool has_independent(const Graph& g,int r) {
    for(unsigned subset=0;subset<(1u<<g.n);++subset) if(popcount(subset)==r) {
        bool ok=true;
        for(int v=0;v<g.n&&ok;++v) if((subset>>v)&1u) {
            if(g.adj[v]&subset) ok=false;
        }
        if(ok) return true;
    }
    return false;
}

static bool admissible_degree9_neighbourhood(const Graph& g) {
    if(g.n!=9) return false;
    for(int v=0;v<9;++v) {
        int d=popcount(g.adj[v]);
        if(d<4 || d==7) return false;
        unsigned nonneighbours=((1u<<9)-1u)&~(g.adj[v]|(1u<<v));
        for(int a=0;a<9;++a) if((nonneighbours>>a)&1u) {
            if((g.adj[a]&nonneighbours)==0) return false;
        }
    }
    if(has_clique(g,4)) return false;
    if(has_independent(g,5)) return false;
    return k_colourable(g,Mask((1u<<9)-1u),3);
}

struct Catalogue {
    std::vector<Graph> graphs;
    long long candidates=0;
    long long raw_admissible=0;
    std::vector<int> unlabeled_counts;
};

static Catalogue generate_degree9_catalogue() {
    std::vector<U64> representatives={0};
    std::vector<int> counts={1};
    for(int n=1;n<8;++n) {
        std::map<U64,U64> unique;
        for(U64 parent_mask:representatives) {
            Graph parent=decode_mask(n,parent_mask);
            for(unsigned neighbourhood=0;neighbourhood<(1u<<n);++neighbourhood) {
                Graph child=parent;
                child.n=n+1;
                for(int v=0;v<n;++v) if((neighbourhood>>v)&1u) {
                    add_edge(child,v,n);
                }
                const U64 key=canonical_small(child);
                if(!unique.count(key)) {
                    std::vector<int> identity(n+1);
                    for(int i=0;i<=n;++i) identity[i]=i;
                    unique[key]=encode_order(child,identity);
                }
            }
        }
        representatives.clear();
        for(const auto& [key,value]:unique) representatives.push_back(value);
        counts.push_back(int(representatives.size()));
    }

    Catalogue result;
    result.unlabeled_counts=counts;
    std::map<U64,U64> admissible;
    for(U64 parent_mask:representatives) {
        Graph parent=decode_mask(8,parent_mask);
        for(unsigned neighbourhood=0;neighbourhood<256;++neighbourhood) {
            ++result.candidates;
            Graph child=parent;
            child.n=9;
            for(int v=0;v<8;++v) if((neighbourhood>>v)&1u) {
                add_edge(child,v,8);
            }
            if(!admissible_degree9_neighbourhood(child)) continue;
            ++result.raw_admissible;
            const U64 key=canonical_small(child);
            if(!admissible.count(key)) {
                std::vector<int> identity(9);
                for(int i=0;i<9;++i) identity[i]=i;
                admissible[key]=encode_order(child,identity);
            }
        }
    }
    for(const auto& [key,value]:admissible) {
        result.graphs.push_back(decode_mask(9,value));
    }
    return result;
}

static bool rainbow_deletion(const Graph& g,int u,int v) {
    Mask remaining=Mask((1u<<g.n)-1u);
    remaining&=Mask(~(Mask(1u<<u)|Mask(1u<<v)));
    Mask common=g.adj[u]&g.adj[v]&remaining;
    if(popcount(common)<4) return false;

    std::array<int,14> colour;
    colour.fill(-1);
    const int total=popcount(remaining);
    std::function<bool(int)> search=[&](int done) {
        unsigned used=0;
        int left=0;
        for(int w=0;w<g.n;++w) if((common>>w)&1u) {
            if(colour[w]>=0) used|=1u<<colour[w];
            else ++left;
        }
        if(popcount(used)+left<4) return false;
        if(done==total) return popcount(used)==4;

        int best=-1,best_sat=-1,best_deg=-1;
        unsigned best_forbidden=0;
        for(int x=0;x<g.n;++x) if(((remaining>>x)&1u)&&colour[x]<0) {
            unsigned forbidden=0;
            for(int y=0;y<g.n;++y) if(colour[y]>=0&&edge(g,x,y)) {
                forbidden|=1u<<colour[y];
            }
            int sat=popcount(forbidden);
            int deg=popcount(g.adj[x]&remaining);
            if(sat>best_sat || (sat==best_sat&&deg>best_deg) ||
               (sat==best_sat&&deg==best_deg&&(best<0||x<best))) {
                best=x;
                best_sat=sat;
                best_deg=deg;
                best_forbidden=forbidden;
            }
        }
        for(int c=0;c<4;++c) if(((best_forbidden>>c)&1u)==0) {
            colour[best]=c;
            if(search(done+1)) return true;
            colour[best]=-1;
        }
        return false;
    };
    return search(0);
}

struct Amalgam {
    Graph graph;
    std::vector<int> neighbours0;
    std::vector<int> neighbours1;
};

static Amalgam build_amalgam(
    const Graph& first,
    int qpos,
    const Graph& second,
    int hpos,
    const std::vector<int>& c1,
    const std::vector<int>& image
) {
    std::array<int,9> map1;
    std::array<int,9> map2;
    map1.fill(-1);
    map2.fill(-1);
    map1[qpos]=1;
    int next=2;
    for(int v=0;v<first.n;++v) if(v!=qpos) map1[v]=next++;
    map2[hpos]=0;
    for(std::size_t i=0;i<c1.size();++i) {
        map2[image[i]]=map1[c1[i]];
    }
    for(int v=0;v<second.n;++v) if(v!=hpos&&map2[v]<0) {
        map2[v]=next++;
    }

    Amalgam result;
    result.graph.n=next;
    for(int v=0;v<first.n;++v) add_edge(result.graph,0,map1[v]);
    for(int v=0;v<second.n;++v) add_edge(result.graph,1,map2[v]);
    for(int u=0;u<first.n;++u) for(int v=u+1;v<first.n;++v) {
        if(edge(first,u,v)) add_edge(result.graph,map1[u],map1[v]);
    }
    for(int u=0;u<second.n;++u) for(int v=u+1;v<second.n;++v) {
        if(edge(second,u,v)) add_edge(result.graph,map2[u],map2[v]);
    }
    for(int v=0;v<first.n;++v) result.neighbours0.push_back(map1[v]);
    for(int v=0;v<second.n;++v) result.neighbours1.push_back(map2[v]);
    return result;
}

static std::string rooted_canonical(const Graph& g) {
    std::vector<int> colour(g.n);
    for(int v=0;v<g.n;++v) {
        if(v==0) colour[v]=0;
        else if(v==1) colour[v]=1;
        else colour[v]=2+popcount(g.adj[v]);
    }
    while(true) {
        std::vector<std::vector<int>> signature(g.n);
        for(int v=0;v<g.n;++v) {
            signature[v].push_back(colour[v]);
            std::vector<int> neighbours;
            for(int w=0;w<g.n;++w) if(edge(g,v,w)) {
                neighbours.push_back(colour[w]);
            }
            std::sort(neighbours.begin(),neighbours.end());
            signature[v].insert(
                signature[v].end(),neighbours.begin(),neighbours.end()
            );
        }
        auto values=signature;
        std::sort(values.begin(),values.end());
        values.erase(std::unique(values.begin(),values.end()),values.end());
        std::vector<int> next(g.n);
        for(int v=0;v<g.n;++v) {
            next[v]=int(
                std::lower_bound(values.begin(),values.end(),signature[v])-values.begin()
            );
        }
        if(next==colour) break;
        colour.swap(next);
    }

    std::map<int,std::vector<int>> cells_by_colour;
    for(int v=0;v<g.n;++v) cells_by_colour[colour[v]].push_back(v);
    std::vector<std::vector<int>> cells;
    for(auto& [c,cell]:cells_by_colour) cells.push_back(cell);
    std::string best;
    bool first=true;
    std::vector<int> order;
    std::function<void(int)> search=[&](int ci) {
        if(ci==int(cells.size())) {
            std::string code;
            code.reserve(g.n*(g.n-1)/2);
            for(int i=0;i<g.n;++i) for(int j=i+1;j<g.n;++j) {
                code.push_back(edge(g,order[i],order[j])?'1':'0');
            }
            if(first||code<best) {
                best=code;
                first=false;
            }
            return;
        }
        auto cell=cells[ci];
        std::sort(cell.begin(),cell.end());
        do {
            order.insert(order.end(),cell.begin(),cell.end());
            search(ci+1);
            order.resize(order.size()-cell.size());
        } while(std::next_permutation(cell.begin(),cell.end()));
    };
    search(0);
    return best;
}

static Graph exceptional_degree9_graph() {
    // graph6 HqolhhX in the encode_mask ordering used here.
    return decode_mask(9,38244599339ULL);
}

static void require(bool condition,const std::string& message) {
    if(!condition) throw std::runtime_error(message);
}

int main() {
    try {
        Catalogue cat=generate_degree9_catalogue();
        const std::vector<int> expected_counts={1,2,4,11,34,156,1044,12346};
        require(cat.unlabeled_counts==expected_counts,"unlabeled graph census mismatch");
        require(cat.candidates==3160576,"candidate count mismatch");
        require(cat.raw_admissible==492,"raw admissible count mismatch");
        require(cat.graphs.size()==67,"admissible type count mismatch");

        const std::array<U64,2> degree8_masks={85450044ULL,95673660ULL};
        std::array<Graph,2> degree8={
            decode_mask(8,degree8_masks[0]),decode_mask(8,degree8_masks[1])
        };

        long long compatible=0;
        long long survivors=0;
        std::set<U64> surviving_d8_types;
        std::set<U64> surviving_d9_types;
        std::set<std::string> rooted_types;
        int surviving_order=-1;
        int surviving_edges=-1;

        for(const Graph& first:degree8) for(int qpos=0;qpos<8;++qpos) {
            std::vector<int> c1;
            for(int v=0;v<8;++v) if(edge(first,qpos,v)) c1.push_back(v);
            for(const Graph& second:cat.graphs) for(int hpos=0;hpos<9;++hpos) {
                std::vector<int> c2;
                for(int v=0;v<9;++v) if(edge(second,hpos,v)) c2.push_back(v);
                if(c1.size()!=c2.size()) continue;
                std::sort(c2.begin(),c2.end());
                do {
                    bool isomorphism=true;
                    for(std::size_t i=0;i<c1.size()&&isomorphism;++i) {
                        for(std::size_t j=i+1;j<c1.size();++j) {
                            if(edge(first,c1[i],c1[j])!=edge(second,c2[i],c2[j])) {
                                isomorphism=false;
                                break;
                            }
                        }
                    }
                    if(!isomorphism) continue;
                    ++compatible;
                    Amalgam amalgam=build_amalgam(
                        first,qpos,second,hpos,c1,c2
                    );
                    bool good=true;
                    for(int x:amalgam.neighbours0) {
                        if(!rainbow_deletion(amalgam.graph,0,x)) {
                            good=false;
                            break;
                        }
                    }
                    if(good) for(int x:amalgam.neighbours1) {
                        if(!rainbow_deletion(amalgam.graph,1,x)) {
                            good=false;
                            break;
                        }
                    }
                    if(!good) continue;
                    ++survivors;
                    surviving_d8_types.insert(canonical_small(first));
                    surviving_d9_types.insert(canonical_small(second));
                    rooted_types.insert(rooted_canonical(amalgam.graph));
                    int edges=0;
                    for(int v=0;v<amalgam.graph.n;++v) {
                        edges+=popcount(amalgam.graph.adj[v]);
                    }
                    edges/=2;
                    if(surviving_order<0) {
                        surviving_order=amalgam.graph.n;
                        surviving_edges=edges;
                    }
                    require(
                        amalgam.graph.n==surviving_order&&edges==surviving_edges,
                        "surviving interface size mismatch"
                    );
                } while(std::next_permutation(c2.begin(),c2.end()));
            }
        }

        require(compatible==4656,"compatible gluing count mismatch");
        require(survivors==8,"surviving gluing count mismatch");
        require(surviving_d8_types.size()==1,
                "unexpected surviving degree-eight types");
        require(surviving_d9_types.size()==1,
                "unexpected surviving degree-nine types");
        require(rooted_types.size()==1,
                "unexpected rooted interface type count");
        require(surviving_order==13&&surviving_edges==39,
                "unexpected interface order or size");
        require(*surviving_d8_types.begin()==canonical_small(degree8[0]),
                "surviving degree-eight graph is not GEnfbW");
        require(
            *surviving_d9_types.begin()==canonical_small(exceptional_degree9_graph()),
            "surviving degree-nine graph is not graph6 HqolhhX"
        );

        std::cout << "unlabeled8 12346\n";
        std::cout << "candidates9 3160576\n";
        std::cout << "raw_admissible9 492\n";
        std::cout << "admissible_types9 67\n";
        std::cout << "compatible_gluings 4656\n";
        std::cout << "surviving_gluings 8\n";
        std::cout << "surviving_degree8_types 1\n";
        std::cout << "surviving_degree9_types 1\n";
        std::cout << "surviving_degree9_graph6 HqolhhX\n";
        std::cout << "rooted_interface_types 1\n";
        std::cout << "interface_vertices 13\n";
        std::cout << "interface_edges 39\n";
        std::cout << "status PASS\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "status FAIL: " << error.what() << "\n";
        return 1;
    }
}
