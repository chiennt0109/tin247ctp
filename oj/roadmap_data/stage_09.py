# path: oj/roadmap_data/stage_09.py

STAGE_9 = {
    "id": 9,
    "title": "🌉 Giai đoạn 9: Đồ thị cơ bản",
    "summary": "Làm quen khái niệm đỉnh, cạnh, cách duyệt đồ thị và tìm liên thông.",
    "topics": [
        {
            "title": "9.1. Biểu diễn đồ thị",
            "summary": "Dùng danh sách kề và ma trận kề để lưu đồ thị trong bộ nhớ.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/9/topic/1/",
            "html_file": "roadmap_data/topics/stage09_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main(){
    int n, m; cin >> n >> m;
    vector<vector<int>> adj(n+1);
    for(int i=0;i<m;i++){
        int u,v; cin>>u>>v;
        adj[u].push_back(v);
        adj[v].push_back(u); // đồ thị vô hướng
    }
    for(int i=1;i<=n;i++){
        cout<<"Đỉnh "<<i<<": ";
        for(int v:adj[i]) cout<<v<<" ";
        cout<<"\\n";
    }
}""",
            "sample_py": """n,m=map(int,input().split())
adj=[[] for _ in range(n+1)]
for _ in range(m):
    u,v=map(int,input().split())
    adj[u].append(v)
    adj[v].append(u)
for i in range(1,n+1):
    print("Đỉnh",i,":",*adj[i])"""
        },
        {
            "title": "9.2. DFS & BFS",
            "summary": "Hai thuật toán duyệt cơ bản giúp hiểu cấu trúc và mối liên kết giữa các đỉnh.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/9/topic/2/",
            "html_file": "roadmap_data/topics/stage09_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int n,m;
vector<vector<int>> adj;
vector<int> visited;

void dfs(int u){
    visited[u]=1;
    cout<<u<<" ";
    for(int v:adj[u])
        if(!visited[v]) dfs(v);
}

void bfs(int start){
    queue<int> q;
    q.push(start);
    visited[start]=1;
    while(!q.empty()){
        int u=q.front(); q.pop();
        cout<<u<<" ";
        for(int v:adj[u])
            if(!visited[v]){
                visited[v]=1;
                q.push(v);
            }
    }
}

int main(){
    cin>>n>>m;
    adj.assign(n+1,{});
    for(int i=0;i<m;i++){
        int u,v;cin>>u>>v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    cout<<"DFS: ";
    visited.assign(n+1,0);
    dfs(1);
    cout<<"\\nBFS: ";
    visited.assign(n+1,0);
    bfs(1);
}""",
            "sample_py": """from collections import deque
n,m=map(int,input().split())
adj=[[] for _ in range(n+1)]
for _ in range(m):
    u,v=map(int,input().split())
    adj[u].append(v)
    adj[v].append(u)

def dfs(u,vis):
    vis[u]=True
    print(u,end=' ')
    for v in adj[u]:
        if not vis[v]:
            dfs(v,vis)

def bfs(start):
    vis=[False]*(n+1)
    q=deque([start])
    vis[start]=True
    while q:
        u=q.popleft()
        print(u,end=' ')
        for v in adj[u]:
            if not vis[v]:
                vis[v]=True
                q.append(v)

print("DFS:",end=' ')
vis=[False]*(n+1)
dfs(1,vis)
print("\\nBFS:",end=' ')
bfs(1)"""
        },
        {
            "title": "9.3. Thành phần liên thông",
            "summary": "Xác định số lượng cụm (component) trong đồ thị vô hướng.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/9/topic/3/",
            "html_file": "roadmap_data/topics/stage09_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int n,m;
vector<vector<int>> adj;
vector<int> vis;

void dfs(int u){
    vis[u]=1;
    for(int v:adj[u])
        if(!vis[v]) dfs(v);
}

int main(){
    cin>>n>>m;
    adj.assign(n+1,{});
    for(int i=0;i<m;i++){
        int u,v;cin>>u>>v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vis.assign(n+1,0);
    int comp=0;
    for(int i=1;i<=n;i++)
        if(!vis[i]){
            comp++;
            dfs(i);
        }
    cout<<"Số thành phần liên thông: "<<comp;
}""",
            "sample_py": """n,m=map(int,input().split())
adj=[[] for _ in range(n+1)]
for _ in range(m):
    u,v=map(int,input().split())
    adj[u].append(v)
    adj[v].append(u)

def dfs(u,vis):
    vis[u]=True
    for v in adj[u]:
        if not vis[v]:
            dfs(v,vis)

vis=[False]*(n+1)
comp=0
for i in range(1,n+1):
    if not vis[i]:
        comp+=1
        dfs(i,vis)
print("Số thành phần liên thông:",comp)"""
        },
    ],
}
