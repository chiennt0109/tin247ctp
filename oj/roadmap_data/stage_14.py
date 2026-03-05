# path: oj/roadmap_data/stage_14.py

STAGE_14 = {
    "id": 14,
    "title": "🚀 Giai đoạn 14: Luyện thi & kỹ năng thi đấu",
    "summary": "Tổng hợp toàn bộ kiến thức để luyện thi HSG, Olympic Tin học và kỹ năng lập trình cạnh tranh.",
    "topics": [
        {
            "title": "14.1. Phân tích & tối ưu độ phức tạp",
            "summary": "Hiểu rõ mối quan hệ giữa thời gian, bộ nhớ và độ phức tạp thuật toán.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/14/topic/1/",
            "html_file": "roadmap_data/topics/stage14_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
// ví dụ đo thời gian chạy brute-force vs tối ưu
long long brute_force_sum(const vector<int>& a){
    long long ans=0;
    for(int i=0;i<a.size();i++)
        for(int j=i;j<a.size();j++)
            for(int k=i;k<=j;k++)
                ans+=a[k];
    return ans;
}
long long prefix_sum_optimized(const vector<int>& a){
    int n=a.size();
    vector<long long> pref(n+1,0);
    for(int i=0;i<n;i++) pref[i+1]=pref[i]+a[i];
    long long ans=0;
    for(int i=0;i<n;i++)
        for(int j=i;j<n;j++)
            ans+=pref[j+1]-pref[i];
    return ans;
}
int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;cin>>n;
    vector<int> a(n);
    for(int i=0;i<n;i++) cin>>a[i];
    cout<<prefix_sum_optimized(a)<<"\\n";
}""",
            "sample_py": """def brute_force_sum(a):
    ans=0
    n=len(a)
    for i in range(n):
        for j in range(i,n):
            for k in range(i,j+1):
                ans+=a[k]
    return ans
def prefix_sum_optimized(a):
    n=len(a)
    pref=[0]*(n+1)
    for i in range(n):
        pref[i+1]=pref[i]+a[i]
    ans=0
    for i in range(n):
        for j in range(i,n):
            ans+=pref[j+1]-pref[i]
    return ans
n=int(input())
arr=list(map(int,input().split()))
print(prefix_sum_optimized(arr))"""
        },
        {
            "title": "14.2. Bài tổng hợp: DP + Graph + Math",
            "summary": "Các bài tập kết hợp nhiều chủ đề, rèn tư duy tổng hợp và khả năng phân tích đề nhanh.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/14/topic/2/",
            "html_file": "roadmap_data/topics/stage14_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
// Ví dụ: đường đi ngắn nhất có ràng buộc chi phí
// graph + dijkstra + kiểm tra điều kiện bằng DP trạng thái
struct Edge{int v,w;};
int main(){
    int n,m;cin>>n>>m;
    vector<vector<Edge>> g(n+1);
    for(int i=0;i<m;i++){
        int u,v,w;cin>>u>>v>>w;
        g[u].push_back({v,w});
        g[v].push_back({u,w});
    }
    const long long INF=1e18;
    vector<long long> dist(n+1,INF);
    priority_queue<pair<long long,int>,vector<pair<long long,int>>,greater<>> pq;
    dist[1]=0; pq.push({0,1});
    while(!pq.empty()){
        auto [d,u]=pq.top();pq.pop();
        if(d!=dist[u]) continue;
        for(auto e:g[u]){
            if(dist[e.v]>d+e.w){
                dist[e.v]=d+e.w;
                pq.push({dist[e.v],e.v});
            }
        }
    }
    cout<<dist[n]<<"\\n";
}""",
            "sample_py": """import heapq
INF=10**18
n,m=map(int,input().split())
g=[[] for _ in range(n+1)]
for _ in range(m):
    u,v,w=map(int,input().split())
    g[u].append((v,w))
    g[v].append((u,w))
dist=[INF]*(n+1)
dist[1]=0
pq=[(0,1)]
while pq:
    d,u=heapq.heappop(pq)
    if d!=dist[u]: continue
    for v,w in g[u]:
        nd=d+w
        if nd<dist[v]:
            dist[v]=nd
            heapq.heappush(pq,(nd,v))
print(dist[n])"""
        },
        {
            "title": "14.3. Kỹ thuật debug & code sạch",
            "summary": "Phương pháp phát hiện lỗi nhanh, viết code rõ ràng và dễ hiểu trong thi đấu.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/14/topic/3/",
            "html_file": "roadmap_data/topics/stage14_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
// mẹo debug: in trạng thái giữa vòng lặp nếu cần
#define dbg(x) cerr<<#x<<" = "<<x<<"\\n"
int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;cin>>n;
    vector<int> a(n);
    for(int i=0;i<n;i++) cin>>a[i];
    sort(a.begin(),a.end());
    dbg(n);
    dbg(a[0]);
    cout<<a.back()-a[0]<<"\\n";
}""",
            "sample_py": """def dbg(name, val):
    print(f"[DBG] {name} = {val}", file=sys.stderr)

import sys
n=int(sys.stdin.readline())
arr=list(map(int,sys.stdin.readline().split()))
arr.sort()
dbg("n", n)
dbg("arr_min", arr[0])
print(arr[-1]-arr[0])"""
        },
        {
            "title": "14.4. Chiến lược thi đấu & quản lý thời gian",
            "summary": "Chiến lược phân tích đề, sắp xếp bài và tối ưu hiệu quả trong các kỳ thi lập trình.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/14/topic/4/",
            "html_file": "roadmap_data/topics/stage14_topic04.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
// Gợi ý in ra kế hoạch làm bài theo độ khó ước lượng
int main(){
    vector<pair<int,string>> prob={
        {1,"Bài A: dễ nhập/xuất, if/for"},
        {2,"Bài B: duyệt + greedy"},
        {3,"Bài C: DP / graph"},
    };
    sort(prob.begin(),prob.end()); // làm từ dễ -> khó
    for(auto &p:prob) cout<<p.second<<"\\n";
}""",
            "sample_py": """problems = [
    (1,"Bài A: dễ, code nhanh, ăn điểm nền tảng"),
    (2,"Bài B: cần ý tưởng tham lam / cấu trúc dữ liệu"),
    (3,"Bài C: bài DP / đồ thị nặng tư duy"),
]
problems.sort()
for _,desc in problems:
    print(desc)"""
        },
    ],
}
