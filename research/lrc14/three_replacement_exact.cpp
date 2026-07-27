#include <bits/stdc++.h>
using namespace std;

// Exact exhaustive search for a counterexample of the form
//   ({1,...,13} \ R) union {x,y,z}, |R|=3, 14<=x<y<z.
// All interval endpoints and all comparisons use rational integer arithmetic.

struct Rat {
    long long n, d;
    Rat(long long nn=0, long long dd=1) {
        if (dd < 0) nn=-nn, dd=-dd;
        if (dd == 0) throw runtime_error("zero denominator");
        long long g = std::gcd(std::llabs(nn), dd);
        n=nn/g; d=dd/g;
    }
};

static bool operator<(const Rat&a,const Rat&b){return (__int128)a.n*b.d < (__int128)b.n*a.d;}
static bool operator==(const Rat&a,const Rat&b){return a.n==b.n && a.d==b.d;}
static bool operator<=(const Rat&a,const Rat&b){return !(b<a);}
static bool operator>(const Rat&a,const Rat&b){return b<a;}
static Rat operator+(const Rat&a,const Rat&b){
    long long g=std::gcd(a.d,b.d);
    __int128 nn=(__int128)a.n*(b.d/g)+(__int128)b.n*(a.d/g);
    __int128 dd=(__int128)(a.d/g)*b.d;
    if (nn>LLONG_MAX||nn<LLONG_MIN||dd>LLONG_MAX) throw runtime_error("Rat overflow");
    return Rat((long long)nn,(long long)dd);
}
static Rat operator-(const Rat&a,const Rat&b){return a+Rat(-b.n,b.d);}
static Rat operator*(const Rat&a,long long k){
    __int128 nn=(__int128)a.n*k;
    if(nn>LLONG_MAX||nn<LLONG_MIN) throw runtime_error("Rat mul overflow");
    return Rat((long long)nn,a.d);
}
static string rs(const Rat&r){return to_string(r.n)+"/"+to_string(r.d);}
static long long floor_rat(const Rat&r){
    long long q=r.n/r.d, rem=r.n%r.d;
    if(rem<0) --q;
    return q;
}
static long long floor_u128(__int128 a,__int128 b){
    if(a<0||b<=0) throw runtime_error("bad floor_u128");
    __int128 q=a/b;
    if(q>LLONG_MAX) return LLONG_MAX;
    return (long long)q;
}

struct Iv { Rat a,b; };

static vector<Iv> normalize(vector<Iv> v){
    sort(v.begin(),v.end(),[](const Iv&x,const Iv&y){
        if(x.a==y.a) return x.b<y.b;
        return x.a<y.a;
    });
    vector<Iv> out;
    for(auto I:v){
        if(I.b<I.a) continue;
        if(out.empty() || out.back().b<I.a) out.push_back(I);
        else if(out.back().b<I.b) out.back().b=I.b;
    }
    return out;
}

// Good set for one speed v on [0,1].  Bad intervals are open neighborhoods
// of k/v of radius 1/(14v), so the complementary intervals are closed.
static vector<Iv> one_speed_good(int v){
    vector<Iv> out; out.reserve(v);
    for(int k=0;k<v;k++){
        out.push_back({Rat(14LL*k+1,14LL*v), Rat(14LL*(k+1)-1,14LL*v)});
    }
    return out;
}

// Intersect a closed interval union with {t: ||v t|| >= 1/14}.
// We subtract the open intervals ((14k-1)/(14v),(14k+1)/(14v)).
static vector<Iv> add_speed(const vector<Iv>& cur,int v){
    vector<Iv> out;
    for(const Iv&I:cur){
        Rat pos=I.a;
        long long k0=max(0LL, floor_rat(I.a*v)-1);
        long long k1=min((long long)v, floor_rat(I.b*v)+1);
        for(long long k=k0;k<=k1;k++){
            Rat l(14*k-1,14LL*v), r(14*k+1,14LL*v);
            if(r<=pos) continue;       // open interval ends at/before current point
            if(I.b<=l) break;          // if equal, endpoint I.b remains good
            if(pos<=l){
                Rat e = (I.b<l ? I.b : l);
                if(pos<=e) out.push_back({pos,e}); // includes possible singleton at l
            }
            if(pos<r) pos=r;           // r itself remains good
            if(I.b<pos) break;
        }
        if(pos<=I.b) out.push_back({pos,I.b});
    }
    return normalize(std::move(out));
}

static vector<Iv> good_set(vector<int> speeds){
    if(speeds.empty()) return {{Rat(0),Rat(1)}};
    sort(speeds.begin(),speeds.end());
    vector<Iv> g=one_speed_good(speeds[0]);
    for(size_t i=1;i<speeds.size();i++) g=add_speed(g,speeds[i]);
    return g;
}

static Rat max_length(const vector<Iv>&g){
    Rat best(0);
    for(const Iv&I:g){ Rat L=I.b-I.a; if(best<L) best=L; }
    return best;
}

// Does one open bad component for speed z contain the whole closed interval I?
static bool component_covered(const Iv&I,int z){
    // Need an integer k with z*b-1/14 < k < z*a+1/14.
    Rat lower=I.b*z-Rat(1,14);
    Rat upper=I.a*z+Rat(1,14);
    long long k=floor_rat(lower)+1;
    return Rat(k,1)<upper;
}

static bool all_covered_by_speed(const vector<Iv>&g,int z){
    if(g.empty()) return true;
    size_t longest=0;
    Rat best=g[0].b-g[0].a;
    for(size_t i=1;i<g.size();i++){
        Rat L=g[i].b-g[i].a;
        if(best<L){best=L;longest=i;}
    }
    if(!component_covered(g[longest],z)) return false;
    for(size_t i=0;i<g.size();i++) if(i!=longest && !component_covered(g[i],z)) return false;
    return true;
}

static long long x_bound(const Rat&L){
    // Counterexample requires x < 3/(2L); floor is a conservative inclusive bound.
    if(L.n<=0) throw runtime_error("zero base interval");
    return floor_u128((__int128)3*L.d,(__int128)2*L.n);
}
static long long y_bound(const Rat&L){
    // Counterexample requires y < 4/(5L).
    if(L.n<=0) throw runtime_error("zero one-added interval");
    return floor_u128((__int128)4*L.d,(__int128)5*L.n);
}
static long long z_bound(const Rat&L){
    // A single open bad interval has length 1/(7z), so it can cover a closed
    // good interval of length L only if z < 1/(7L).
    if(L.n<=0) throw runtime_error("zero two-added interval");
    return floor_u128((__int128)L.d,(__int128)7*L.n);
}

struct Counts {
    unsigned long long removed=0,x=0,y=0,z_range=0,z_t14=0,z_exact=0;
};

int main(int argc,char**argv){
    int shard=0,nshards=1;
    string outpath="result.json";
    if(argc>=2) shard=stoi(argv[1]);
    if(argc>=3) nshards=stoi(argv[2]);
    if(argc>=4) outpath=argv[3];
    if(shard<0||shard>=nshards||nshards<=0) return 2;

    vector<array<int,3>> rems;
    for(int a=1;a<=13;a++)for(int b=a+1;b<=13;b++)for(int c=b+1;c<=13;c++)rems.push_back({a,b,c});
    Counts C;
    long long global_xmax=0,global_ymax=0,global_zmax=0;
    size_t max_base_components=0,max_g1_components=0,max_g2_components=0;
    auto start=chrono::steady_clock::now();

    for(size_t ri=0;ri<rems.size();ri++){
        if((int)(ri%nshards)!=shard) continue;
        auto R=rems[ri]; C.removed++;
        vector<int> W;
        for(int v=1;v<=13;v++) if(v!=R[0]&&v!=R[1]&&v!=R[2]) W.push_back(v);
        vector<Iv> G0=good_set(W);
        max_base_components=max(max_base_components,G0.size());
        Rat L0=max_length(G0);
        long long xmax=max(13LL,x_bound(L0));
        global_xmax=max(global_xmax,xmax);

        for(int x=14;x<=xmax;x++){
            C.x++;
            vector<Iv> G1=add_speed(G0,x);
            max_g1_components=max(max_g1_components,G1.size());
            Rat L1=max_length(G1);
            long long ymax=y_bound(L1);
            global_ymax=max(global_ymax,ymax);
            if(ymax<=x) continue;

            for(int y=x+1;y<=ymax;y++){
                C.y++;
                vector<Iv> G2=add_speed(G1,y);
                max_g2_components=max(max_g2_components,G2.size());
                Rat L2=max_length(G2);
                long long zmax=z_bound(L2);
                global_zmax=max(global_zmax,zmax);
                if(zmax<=y) continue;
                C.z_range += (unsigned long long)(zmax-y);

                if(x%14!=0 && y%14!=0){
                    int z=((y/14)+1)*14;
                    C.z_t14 += (unsigned long long)(zmax-y) - (z<=zmax ? (unsigned long long)((zmax-z)/14+1) : 0ULL);
                    for(;z<=zmax;z+=14){
                        C.z_exact++;
                        if(all_covered_by_speed(G2,z)){
                            ofstream f(outpath);
                            f<<"{\n  \"status\": \"COUNTEREXAMPLE\",\n";
                            f<<"  \"removed\": ["<<R[0]<<","<<R[1]<<","<<R[2]<<"],\n";
                            f<<"  \"added\": ["<<x<<","<<y<<","<<z<<"],\n";
                            f<<"  \"base_max_interval\": \""<<rs(L0)<<"\",\n";
                            f<<"  \"one_added_max_interval\": \""<<rs(L1)<<"\",\n";
                            f<<"  \"two_added_max_interval\": \""<<rs(L2)<<"\"\n}\n";
                            cout<<"COUNTEREXAMPLE R="<<R[0]<<","<<R[1]<<","<<R[2]
                                <<" X="<<x<<","<<y<<","<<z<<"\n";
                            return 10;
                        }
                    }
                }else{
                    for(int z=y+1;z<=zmax;z++){
                        C.z_exact++;
                        if(all_covered_by_speed(G2,z)){
                            ofstream f(outpath);
                            f<<"{\n  \"status\": \"COUNTEREXAMPLE\",\n";
                            f<<"  \"removed\": ["<<R[0]<<","<<R[1]<<","<<R[2]<<"],\n";
                            f<<"  \"added\": ["<<x<<","<<y<<","<<z<<"],\n";
                            f<<"  \"base_max_interval\": \""<<rs(L0)<<"\",\n";
                            f<<"  \"one_added_max_interval\": \""<<rs(L1)<<"\",\n";
                            f<<"  \"two_added_max_interval\": \""<<rs(L2)<<"\"\n}\n";
                            cout<<"COUNTEREXAMPLE R="<<R[0]<<","<<R[1]<<","<<R[2]
                                <<" X="<<x<<","<<y<<","<<z<<"\n";
                            return 10;
                        }
                    }
                }
            }
        }
        double sec=chrono::duration<double>(chrono::steady_clock::now()-start).count();
        cerr<<"shard "<<shard<<" Rindex "<<ri<<" removed "<<R[0]<<","<<R[1]<<","<<R[2]
            <<" x="<<C.x<<" y="<<C.y<<" zexact="<<C.z_exact<<" sec="<<fixed<<setprecision(2)<<sec<<"\n";
    }

    double sec=chrono::duration<double>(chrono::steady_clock::now()-start).count();
    ofstream f(outpath);
    f<<"{\n";
    f<<"  \"status\": \"NO_COUNTEREXAMPLE\",\n";
    f<<"  \"shard\": "<<shard<<",\n  \"nshards\": "<<nshards<<",\n";
    f<<"  \"removed_triples\": "<<C.removed<<",\n";
    f<<"  \"x_values\": "<<C.x<<",\n  \"y_values\": "<<C.y<<",\n";
    f<<"  \"z_range_values\": "<<C.z_range<<",\n";
    f<<"  \"z_eliminated_by_t_1_14\": "<<C.z_t14<<",\n";
    f<<"  \"z_exact_tests\": "<<C.z_exact<<",\n";
    f<<"  \"global_x_bound\": "<<global_xmax<<",\n";
    f<<"  \"global_y_bound\": "<<global_ymax<<",\n";
    f<<"  \"global_z_bound\": "<<global_zmax<<",\n";
    f<<"  \"max_base_components\": "<<max_base_components<<",\n";
    f<<"  \"max_one_added_components\": "<<max_g1_components<<",\n";
    f<<"  \"max_two_added_components\": "<<max_g2_components<<",\n";
    f<<"  \"seconds\": "<<fixed<<setprecision(6)<<sec<<"\n}\n";
    cout<<"NO_COUNTEREXAMPLE shard="<<shard<<"/"<<nshards
        <<" R="<<C.removed<<" x="<<C.x<<" y="<<C.y
        <<" zrange="<<C.z_range<<" t14="<<C.z_t14<<" exact="<<C.z_exact
        <<" xmax="<<global_xmax<<" ymax="<<global_ymax<<" zmax="<<global_zmax
        <<" sec="<<fixed<<setprecision(2)<<sec<<"\n";
    return 0;
}
