# path: oj/roadmap_data/stage_06.py

STAGE_6 = {
    "id": 6,
    "title": "📈 Giai đoạn 6: Quy hoạch động (Dynamic Programming)",
    "summary": "Tối ưu hóa bài toán bằng cách ghi nhớ trạng thái và kết quả trung gian.",
    "topics": [
        {
            "title": "6.1. Fibonacci tối ưu (Memoization)",
            "summary": "Hiểu cách giảm số lần tính toán lặp bằng cách lưu kết quả trung gian.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/6/topic/1/",
            "html_file": "roadmap_data/topics/stage06_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
vector<long long> f(100, -1);
long long fib(int n) {
    if (n <= 1) return n;
    if (f[n] != -1) return f[n];
    return f[n] = fib(n - 1) + fib(n - 2);
}
int main() {
    int n; cin >> n;
    cout << fib(n);
}""",
            "sample_py": """from functools import lru_cache
@lru_cache(maxsize=None)
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
print(fib(int(input())))"""
        },
        {
            "title": "6.2. Bài toán Balo (Knapsack)",
            "summary": "Giải bài toán chọn vật phẩm tối ưu bằng kỹ thuật DP 2 chiều.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/6/topic/2/",
            "html_file": "roadmap_data/topics/stage06_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, W; cin >> n >> W;
    vector<int> w(n+1), v(n+1);
    for (int i = 1; i <= n; i++) cin >> w[i] >> v[i];
    vector<vector<int>> dp(n+1, vector<int>(W+1, 0));
    for (int i = 1; i <= n; i++)
        for (int j = 0; j <= W; j++)
            if (j >= w[i])
                dp[i][j] = max(dp[i-1][j], dp[i-1][j-w[i]] + v[i]);
            else dp[i][j] = dp[i-1][j];
    cout << dp[n][W];
}""",
            "sample_py": """n, W = map(int, input().split())
w, v = [0], [0]
for _ in range(n):
    wi, vi = map(int, input().split())
    w.append(wi); v.append(vi)
dp = [[0]*(W+1) for _ in range(n+1)]
for i in range(1, n+1):
    for j in range(W+1):
        if j >= w[i]:
            dp[i][j] = max(dp[i-1][j], dp[i-1][j-w[i]] + v[i])
        else:
            dp[i][j] = dp[i-1][j]
print(dp[n][W])"""
        },
        {
            "title": "6.3. Dãy con tăng dài nhất (LIS)",
            "summary": "Xây dựng lời giải quy hoạch động để tìm dãy con tăng dài nhất.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/6/topic/3/",
            "html_file": "roadmap_data/topics/stage06_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    vector<int> dp(n, 1);
    for (int i = 1; i < n; i++)
        for (int j = 0; j < i; j++)
            if (a[i] > a[j])
                dp[i] = max(dp[i], dp[j] + 1);
    cout << *max_element(dp.begin(), dp.end());
}""",
            "sample_py": """n = int(input())
a = list(map(int, input().split()))
dp = [1]*n
for i in range(1,n):
    for j in range(i):
        if a[i]>a[j]:
            dp[i] = max(dp[i], dp[j]+1)
print(max(dp))"""
        },
    ],
}
