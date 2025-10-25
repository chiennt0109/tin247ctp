# path: oj/roadmap_data/stage_10.py

STAGE_10 = {
    "id": 10,
    "title": "🌍 Giai đoạn 10: Đồ thị nâng cao",
    "summary": "Học các thuật toán tìm đường, cây bao trùm nhỏ nhất và đồ thị có trọng số.",
    "topics": [
        {
            "title": "10.1. Dijkstra, Bellman-Ford",
            "summary": "Tìm đường đi ngắn nhất trong đồ thị có trọng số dương hoặc âm.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/10/topic/1/",
            "html_file": "roadmap_data/topics/stage10_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main(){
    int n,m; cin>>n>>m;
    vector<vector<pair<int,int>>> adj(n+1);
    for(int i=0;i<m;i++){
        int u,v,w; cin>>u>>v>>w;
        adj[u].push_back({v,w});
    }
    vector<int> dist(n+1,1e9);
    dist[1]=0;
    priority_queue<pair<int,int>,vector<pair<int,int>>,greater<>> pq;
    pq.push({0,1});
    while(!pq.empty()){
        auto [d,u]=pq.top(); pq.pop();
        if(d!=dist[u]) continue;
        for(auto [v,w]:adj[u]){
            if(dist[v]>d+w){
                dist[v]=d+w;
                pq.push({dist[v],v});
            }
        }
    }
    for(int i=1;i<=n;i++) cout<<"dist["<<i<<"]="<<dist[i]<<"\\n";
}""",
            "sample_py": """import heapq
n,m=map(int,input().split())
adj=[[] for _ in range(n+1)]
for _ in range(m):
    u,v,w=map(int,input().split())
    adj[u].append((v,w))
dist=[10**9]*(n+1)
dist[1]=0
pq=[(0,1)]
while pq:
    d,u=heapq.heappop(pq)
    if d!=dist[u]: continue
    for v,w in adj[u]:
        if dist[v]>d+w:
            dist[v]=d+w
            heapq.heappush(pq,(dist[v],v))
for i in range(1,n+1):
    print("dist[{}]={}".format(i,dist[i]))"""
        },
        {
            "title": "10.2. Floyd–Warshall",
            "summary": "Tìm đường đi ngắn nhất giữa mọi cặp đỉnh trong đồ thị nhỏ.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/10/topic/2/",
            "html_file": "roadmap_data/topics/stage10_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main(){
    int n,m; cin>>n>>m;
    const int INF=1e9;
    vector<vector<int>> dist(n+1,vector<int>(n+1,INF));
    for(int i=1;i<=n;i++) dist[i][i]=0;
    for(int i=0;i<m;i++){
        int u,v,w;cin>>u>>v>>w;
        dist[u][v]=min(dist[u][v],w);
    }
    for(int k=1;k<=n;k++)
        for(int i=1;i<=n;i++)
            for(int j=1;j<=n;j++)
                if(dist[i][k]<INF && dist[k][j]<INF)
                    dist[i][j]=min(dist[i][j],dist[i][k]+dist[k][j]);
    for(int i=1;i<=n;i++){
        for(int j=1;j<=n;j++){
            if(dist[i][j]==INF) cout<<"INF ";
            else cout<<dist[i][j]<<" ";
        }
        cout<<"\\n";
    }
}""",
            "sample_py": """INF=10**9
n,m=map(int,input().split())
dist=[[INF]*(n+1) for _ in range(n+1)]
for i in range(1,n+1): dist[i][i]=0
for _ in range(m):
    u,v,w=map(int,input().split())
    dist[u][v]=min(dist[u][v],w)
for k in range(1,n+1):
    for i in range(1,n+1):
        for j in range(1,n+1):
            if dist[i][k]<INF and dist[k][j]<INF:
                dist[i][j]=min(dist[i][j],dist[i][k]+dist[k][j])
for i in range(1,n+1):
    print(*[x if x<INF else "INF" for x in dist[i][1:]])"""
        },
        {
            "title": "10.3. MST: Kruskal & Prim",
            "summary": "Tạo cây bao trùm nhỏ nhất cho mạng kết nối bằng thuật toán tham lam.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/10/topic/3/",
            "html_file": "roadmap_data/topics/stage10_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
struct Edge{int u,v,w;};
struct DSU{
    vector<int> p;
    DSU(int n){p.resize(n+1);iota(p.begin(),p.end(),0);}
    int find(int x){return p[x]==x?x:p[x]=find(p[x]);}
    bool unite(int a,int b){
        a=find(a);b=find(b);
        if(a==b) return false;
        p[b]=a; return true;
    }
};
int main(){
    int n,m;cin>>n>>m;
    vector<Edge> edges(m);
    for(auto &e:edges) cin>>e.u>>e.v>>e.w;
    sort(edges.begin(),edges.end(),[](auto &a,auto &b){return a.w<b.w;});
    DSU dsu(n);
    int total=0;
    for(auto &e:edges)
        if(dsu.unite(e.u,e.v)) total+=e.w;
    cout<<"MST weight="<<total;
}""",
            "sample_py": """n,m=map(int,input().split())
edges=[tuple(map(int,input().split())) for _ in range(m)]
edges.sort(key=lambda x:x[2])
parent=list(range(n+1))
def find(x):
    if parent[x]!=x:
        parent[x]=find(parent[x])
    return parent[x]
def unite(a,b):
    a,b=find(a),find(b)
    if a==b: return False
    parent[b]=a
    return True
total=0
for u,v,w in edges:
    if unite(u,v): total+=w
print("MST weight=",total)"""
        },
    ],
}
