#include <bits/stdc++.h>
using namespace std;
struct Rat{long long n,d;Rat(long long a=0,long long b=1){if(b<0)a=-a,b=-b;if(!b)throw runtime_error("0den");long long g=gcd(llabs(a),b);n=a/g;d=b/g;}};
static bool operator<(Rat a,Rat b){return (__int128)a.n*b.d<(__int128)b.n*a.d;}static bool operator==(Rat a,Rat b){return a.n==b.n&&a.d==b.d;}static bool operator<=(Rat a,Rat b){return !(b<a);}static Rat operator+(Rat a,Rat b){long long g=gcd(a.d,b.d);__int128 n=(__int128)a.n*(b.d/g)+(__int128)b.n*(a.d/g),d=(__int128)(a.d/g)*b.d;if(n>LLONG_MAX||n<LLONG_MIN||d>LLONG_MAX)throw runtime_error("ov");return Rat((long long)n,(long long)d);}static Rat operator-(Rat a,Rat b){return a+Rat(-b.n,b.d);}static Rat operator*(Rat a,long long k){__int128 n=(__int128)a.n*k;if(n>LLONG_MAX||n<LLONG_MIN)throw runtime_error("ov");return Rat((long long)n,a.d);}static long long fl(Rat a){long long q=a.n/a.d,r=a.n%a.d;if(r<0)--q;return q;}static long long qfloor(__int128 a,__int128 b){if(a<0||b<=0)throw runtime_error("bad");__int128 q=a/b;return q>LLONG_MAX?LLONG_MAX:(long long)q;}
struct Iv{Rat a,b;};
static vector<Iv> norm(vector<Iv>v){sort(v.begin(),v.end(),[](auto x,auto y){return x.a==y.a?x.b<y.b:x.a<y.a;});vector<Iv>o;for(auto I:v){if(I.b<I.a)continue;if(o.empty()||o.back().b<I.a)o.push_back(I);else if(o.back().b<I.b)o.back().b=I.b;}return o;}
static vector<Iv> one(int v){vector<Iv>o;for(int k=0;k<v;k++)o.push_back({Rat(14LL*k+1,14LL*v),Rat(14LL*(k+1)-1,14LL*v)});return o;}
static vector<Iv> add(const vector<Iv>&c,int v){vector<Iv>o;for(auto I:c){Rat p=I.a;long long k0=max(0LL,fl(I.a*v)-1),k1=min((long long)v,fl(I.b*v)+1);for(long long k=k0;k<=k1;k++){Rat l(14*k-1,14LL*v),r(14*k+1,14LL*v);if(r<=p)continue;if(I.b<=l)break;if(p<=l){Rat e=I.b<l?I.b:l;if(p<=e)o.push_back({p,e});}if(p<r)p=r;if(I.b<p)break;}if(p<=I.b)o.push_back({p,I.b});}return norm(move(o));}
static vector<Iv> good(vector<int>s){sort(s.begin(),s.end());vector<Iv>g=one(s[0]);for(size_t i=1;i<s.size();i++)g=add(g,s[i]);return g;}
static Rat maxlen(const vector<Iv>&g){Rat b(0);for(auto I:g){Rat L=I.b-I.a;if(b<L)b=L;}return b;}
static bool compcov(Iv I,int z){Rat lo=I.b*z-Rat(1,14),hi=I.a*z+Rat(1,14);long long k=fl(lo)+1;return Rat(k)<hi;}
static bool covered(const vector<Iv>&g,int z){for(auto I:g)if(!compcov(I,z))return false;return true;}
static long long bound_r(Rat L,int r){ // r>=2 remaining speeds, smallest next speed n: n < 2r/((7-r)L)
 if(L.n<=0)throw runtime_error("L0");return qfloor((__int128)2*r*L.d,(__int128)(7-r)*L.n);
}
static long long lastbound(Rat L){if(L.n<=0)throw runtime_error("L0");return qfloor((__int128)L.d,(__int128)7*L.n);}
int main(int ac,char**av){int sh=ac>1?stoi(av[1]):0,ns=ac>2?stoi(av[2]):1;string out=ac>3?av[3]:"result.json";if(sh<0||sh>=ns)return 2;vector<array<int,4>>Rs;for(int a=1;a<=13;a++)for(int b=a+1;b<=13;b++)for(int c=b+1;c<=13;c++)for(int d=c+1;d<=13;d++)Rs.push_back({a,b,c,d});unsigned long long nr=0,nx=0,ny=0,nz=0,nw=0;long long X=0,Y=0,Z=0,W=0;auto t0=chrono::steady_clock::now();
 for(size_t ri=0;ri<Rs.size();ri++){if((int)(ri%ns)!=sh)continue;nr++;auto R=Rs[ri];vector<int>B;for(int v=1;v<=13;v++)if(v!=R[0]&&v!=R[1]&&v!=R[2]&&v!=R[3])B.push_back(v);auto G0=good(B);long long xb=max(13LL,bound_r(maxlen(G0),4));X=max(X,xb);
  for(int x=14;x<=xb;x++){nx++;auto G1=add(G0,x);long long yb=bound_r(maxlen(G1),3);Y=max(Y,yb);if(yb<=x)continue;
   for(int y=x+1;y<=yb;y++){ny++;auto G2=add(G1,y);long long zb=bound_r(maxlen(G2),2);Z=max(Z,zb);if(zb<=y)continue;
    for(int z=y+1;z<=zb;z++){nz++;auto G3=add(G2,z);long long wb=lastbound(maxlen(G3));W=max(W,wb);if(wb<=z)continue;
     bool first3_non14=x%14&&y%14&&z%14;int w0=z+1,step=1;if(first3_non14){w0=((z/14)+1)*14;step=14;}
     for(int w=w0;w<=wb;w+=step){nw++;if(covered(G3,w)){ofstream f(out);f<<"{\n\"status\":\"COUNTEREXAMPLE\",\n\"removed\":["<<R[0]<<","<<R[1]<<","<<R[2]<<","<<R[3]<<"],\n\"added\":["<<x<<","<<y<<","<<z<<","<<w<<"]\n}\n";cout<<"COUNTEREXAMPLE\n";return 10;}}
    }
   }
  }
  cerr<<"shard "<<sh<<" ri "<<ri<<" R "<<nr<<" x "<<nx<<" y "<<ny<<" z "<<nz<<" w "<<nw<<" sec "<<chrono::duration<double>(chrono::steady_clock::now()-t0).count()<<"\n";
 }
 double sec=chrono::duration<double>(chrono::steady_clock::now()-t0).count();ofstream f(out);f<<"{\n\"status\":\"NO_COUNTEREXAMPLE\",\n\"shard\":"<<sh<<",\n\"nshards\":"<<ns<<",\n\"removed_quadruples\":"<<nr<<",\n\"x_values\":"<<nx<<",\n\"y_values\":"<<ny<<",\n\"z_values\":"<<nz<<",\n\"w_exact_tests\":"<<nw<<",\n\"global_bounds\":["<<X<<","<<Y<<","<<Z<<","<<W<<"],\n\"seconds\":"<<fixed<<setprecision(6)<<sec<<"\n}\n";cout<<"NO_COUNTEREXAMPLE shard="<<sh<<" R="<<nr<<" x="<<nx<<" y="<<ny<<" z="<<nz<<" w="<<nw<<" bounds="<<X<<","<<Y<<","<<Z<<","<<W<<" sec="<<sec<<"\n";
}
