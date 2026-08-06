#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using Mask = std::uint16_t;
using Adj = std::array<Mask, 14>;
using Edge = std::pair<int,int>;

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

static int popcount(Mask x) {
    return __builtin_popcount(static_cast<unsigned>(x));
}

static void add_edge(Adj& adj, int u, int v) {
    adj[u] |= Mask(1u << v);
    adj[v] |= Mask(1u << u);
}

static Adj graph_from_cross_mask(int cross_mask) {
    Adj adj{};
    for (auto [u,v] : BASE) add_edge(adj,u,v);
    for (int bit=0; bit<12; ++bit) if ((cross_mask >> bit) & 1) {
        add_edge(adj,CROSS[bit].first,CROSS[bit].second);
    }
    return adj;
}

static bool edge(const Adj& adj, int u, int v) {
    return ((adj[u] >> v) & 1u) != 0;
}

static bool k_colourable(const Adj& adj, Mask vertices, int k) {
    std::array<int,14> colour;
    colour.fill(-1);
    const int total = popcount(vertices);

    auto search = [&](auto&& self, int done) -> bool {
        if (done == total) return true;
        int best=-1, best_sat=-1, best_deg=-1;
        Mask best_forbidden=0;
        for (int v=0; v<14; ++v) if (((vertices>>v)&1u) && colour[v]<0) {
            Mask forbidden=0;
            for (int w=0; w<14; ++w) if (colour[w]>=0 && edge(adj,v,w)) {
                forbidden |= Mask(1u << colour[w]);
            }
            const int sat=popcount(forbidden);
            const int deg=popcount(adj[v] & vertices);
            if (sat>best_sat || (sat==best_sat && deg>best_deg) ||
                (sat==best_sat && deg==best_deg && (best<0 || v<best))) {
                best=v;
                best_sat=sat;
                best_deg=deg;
                best_forbidden=forbidden;
            }
        }
        for (int c=0; c<k; ++c) if (((best_forbidden>>c)&1u)==0) {
            colour[best]=c;
            if (self(self,done+1)) return true;
            colour[best]=-1;
        }
        return false;
    };
    return search(search,0);
}

static bool rainbow_deletion(const Adj& adj, int u, int v) {
    Mask remaining = Mask((1u<<13)-1u);
    remaining &= Mask(~(Mask(1u<<u)|Mask(1u<<v)));
    const Mask common = adj[u] & adj[v] & remaining;
    if (popcount(common)<4) return false;

    std::array<int,14> colour;
    colour.fill(-1);
    const int total=popcount(remaining);
    auto search = [&](auto&& self, int done) -> bool {
        Mask used=0;
        int uncoloured_common=0;
        for (int w=0; w<13; ++w) if ((common>>w)&1u) {
            if (colour[w]>=0) used |= Mask(1u<<colour[w]);
            else ++uncoloured_common;
        }
        if (popcount(used)+uncoloured_common<4) return false;
        if (done==total) return popcount(used)==4;

        int best=-1,best_sat=-1,best_deg=-1;
        Mask best_forbidden=0;
        for (int x=0;x<13;++x) if (((remaining>>x)&1u) && colour[x]<0) {
            Mask forbidden=0;
            for (int y=0;y<13;++y) if (colour[y]>=0 && edge(adj,x,y)) {
                forbidden |= Mask(1u<<colour[y]);
            }
            int sat=popcount(forbidden), deg=popcount(adj[x]&remaining);
            if (sat>best_sat || (sat==best_sat && deg>best_deg) ||
                (sat==best_sat && deg==best_deg && (best<0 || x<best))) {
                best=x;
                best_sat=sat;
                best_deg=deg;
                best_forbidden=forbidden;
            }
        }
        for(int c=0;c<4;++c) if(((best_forbidden>>c)&1u)==0) {
            colour[best]=c;
            if(self(self,done+1)) return true;
            colour[best]=-1;
        }
        return false;
    };
    return search(search,0);
}

static bool has_k5(const Adj& adj) {
    for(int a=0;a<13;++a) for(int b=a+1;b<13;++b) if(edge(adj,a,b))
    for(int c=b+1;c<13;++c) if(edge(adj,a,c)&&edge(adj,b,c))
    for(int d=c+1;d<13;++d) if(edge(adj,a,d)&&edge(adj,b,d)&&edge(adj,c,d))
    for(int e=d+1;e<13;++e)
        if(edge(adj,a,e)&&edge(adj,b,e)&&edge(adj,c,e)&&edge(adj,d,e)) return true;
    return false;
}

static bool local_three_colourable(const Adj& adj) {
    const Mask interface_vertices=Mask((1u<<13)-1u);
    for(int v=0;v<13;++v) {
        if(!k_colourable(adj,adj[v]&interface_vertices,3)) return false;
    }
    return true;
}

static bool residual_interface(const Adj& adj) {
    for(int x=0;x<13;++x) if(edge(adj,0,x) && !rainbow_deletion(adj,0,x)) return false;
    for(int x=0;x<13;++x) if(edge(adj,1,x) && !rainbow_deletion(adj,1,x)) return false;
    return !has_k5(adj) && local_three_colourable(adj);
}

static bool allowed_outside_neighbourhood(const Adj& interface_adj, Mask S) {
    if (!k_colourable(interface_adj,S,3)) return false;

    for(int v=2;v<13;++v) if((S>>v)&1u) {
        Adj augmented=interface_adj;
        const Mask trace = S & interface_adj[v];
        for(int w=0;w<13;++w) if((trace>>w)&1u) add_edge(augmented,13,w);
        const Mask local_vertices =
            (interface_adj[v]&Mask((1u<<13)-1u)) | Mask(1u<<13);
        if(!k_colourable(augmented,local_vertices,3)) return false;
    }
    return true;
}

struct Requirement {
    Mask trace;
    int demand;
};

static std::vector<Requirement> requirements(const Adj& adj) {
    std::vector<Requirement> req;
    const Mask interface_vertices=Mask((1u<<13)-1u);
    for(int v=2;v<13;++v) {
        int d=std::max(0,8-popcount(adj[v]&interface_vertices));
        if(d) req.push_back({Mask(1u<<v),d});
    }
    for(int u=0;u<13;++u) for(int v=u+1;v<13;++v) if(edge(adj,u,v)) {
        int internal=popcount(adj[u]&adj[v]&interface_vertices);
        int d=std::max(0,4-internal);
        if(d) req.push_back({Mask((1u<<u)|(1u<<v)),d});
    }
    return req;
}

static bool four_outside_vertices_suffice(
    const Adj& adj,
    int& allowed_count,
    int& maximal_count
) {
    std::vector<Mask> allowed;
    for(int raw=0;raw<(1<<11);++raw) {
        Mask S=0;
        for(int i=0;i<11;++i) if((raw>>i)&1) S|=Mask(1u<<(i+2));
        if(allowed_outside_neighbourhood(adj,S)) allowed.push_back(S);
    }
    allowed_count=static_cast<int>(allowed.size());

    std::vector<Mask> maximal;
    for(Mask S:allowed) {
        bool extendable=false;
        for(int v=2;v<13;++v) if(((S>>v)&1u)==0) {
            const Mask T=S|Mask(1u<<v);
            if(std::binary_search(allowed.begin(),allowed.end(),T)) {
                extendable=true;
                break;
            }
        }
        if(!extendable) maximal.push_back(S);
    }
    maximal_count=static_cast<int>(maximal.size());
    const auto req=requirements(adj);

    const int m=static_cast<int>(maximal.size());
    for(int a=0;a<m;++a) for(int b=a;b<m;++b)
    for(int c=b;c<m;++c) for(int d=c;d<m;++d) {
        const std::array<Mask,4> chosen={maximal[a],maximal[b],maximal[c],maximal[d]};
        bool ok=true;
        for(const auto& r:req) {
            int have=0;
            for(Mask S:chosen) if((S&r.trace)==r.trace) ++have;
            if(have<r.demand) {
                ok=false;
                break;
            }
        }
        if(ok) return true;
    }
    return false;
}

static std::vector<int> common(const Adj& adj,int u,int v) {
    std::vector<int> out;
    Mask C=adj[u]&adj[v]&Mask((1u<<13)-1u);
    for(int w=0;w<13;++w) if((C>>w)&1u) out.push_back(w);
    return out;
}

static void require(bool value,const std::string& message) {
    if(!value) throw std::runtime_error(message);
}

int main() {
    try {
        std::vector<int> survivors;
        for(int mask=0;mask<(1<<12);++mask) {
            const Adj adj=graph_from_cross_mask(mask);
            if(residual_interface(adj)) survivors.push_back(mask);
        }
        const std::vector<int> expected={
            0,1,16,17,64,65,128,129,512,513,528,529,576,577,640,641
        };
        require(survivors==expected,"unexpected 4096-mask survivor census");

        std::vector<int> residual;
        for(int mask:survivors) {
            const Adj adj=graph_from_cross_mask(mask);
            int allowed_count=0,maximal_count=0;
            const bool feasible=four_outside_vertices_suffice(
                adj,allowed_count,maximal_count
            );
            require(allowed_count==1864,"unexpected allowed-neighbourhood count");
            require(maximal_count==13,"unexpected maximal-neighbourhood count");
            if(feasible) residual.push_back(mask);
        }
        const std::vector<int> expected_residual={0,16,17,64,128};
        require(residual==expected_residual,"unexpected four-outside residual masks");

        for(int mask:residual) {
            const Adj adj=graph_from_cross_mask(mask);
            require(popcount(adj[0])==8 && popcount(adj[1])==9,
                    "centre degree mismatch");
            require(edge(adj,4,6)&&edge(adj,4,8)&&edge(adj,6,8),
                    "triangle 4,6,8 missing");
            if(mask==0) {
                require(
                    popcount(adj[4])==5&&popcount(adj[6])==5&&popcount(adj[8])==5,
                    "mask 0 degree-five triangle mismatch"
                );
            } else {
                require(popcount(adj[8])==5,
                        "vertex 8 must have interface degree five");
                require(popcount(adj[4])<=6,
                        "vertex 4 must have interface degree at most six");
                require(common(adj,5,12)==std::vector<int>({1,2}),
                        "common(5,12) mismatch");
                require(edge(adj,0,4)&&edge(adj,0,8)&&edge(adj,4,8),
                        "triangle 0,4,8 missing");
                require(edge(adj,0,1)&&edge(adj,0,2)&&edge(adj,1,2),
                        "triangle 0,1,2 missing");
                require(edge(adj,1,2)&&edge(adj,1,12)&&edge(adj,2,12),
                        "triangle 1,2,12 missing");
            }
        }

        std::cout << "cross_masks 4096\n";
        std::cout << "rainbow_survivors " << survivors.size() << "\n";
        std::cout << "survivor_masks";
        for(int m:survivors) std::cout << ' ' << m;
        std::cout << "\n";
        std::cout << "allowed_neighbourhoods 1864\n";
        std::cout << "maximal_neighbourhoods 13\n";
        std::cout << "four_outside_feasible " << residual.size() << "\n";
        std::cout << "residual_masks";
        for(int m:residual) std::cout << ' ' << m;
        std::cout << "\n";
        std::cout << "symbolic_facts PASS\n";
        std::cout << "status PASS\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "status FAIL: " << error.what() << "\n";
        return 1;
    }
}
