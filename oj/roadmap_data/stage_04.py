# path: oj/roadmap_data/stage_04.py

STAGE_4 = {
    "id": 4,
    "title": "🧠 Giai đoạn 4: Tư duy giải thuật & bài toán thực tế",
    "summary": "Áp dụng thuật toán vào các bài toán mô phỏng, thống kê, và xử lý dữ liệu thực tế.",
    "topics": [
        {
            "title": "4.1. Bài toán đếm & tính toán",
            "summary": "Sử dụng vòng lặp, điều kiện để tính tổng, đếm số lượng, tìm giá trị lớn nhất, nhỏ nhất.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/4/topic/1/",
            "html_file": "roadmap_data/topics/stage04_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    int sum = 0, mx = a[0], mn = a[0];
    for (int x : a) {
        sum += x;
        mx = max(mx, x);
        mn = min(mn, x);
    }
    cout << "Tong=" << sum << " Max=" << mx << " Min=" << mn;
}""",
            "sample_py": """n = int(input())
a = list(map(int, input().split()))
print("Tong =", sum(a), "Max =", max(a), "Min =", min(a))"""
        },
        {
            "title": "4.2. Thống kê & tìm kiếm dữ liệu",
            "summary": "Làm quen với bài toán phân tích dữ liệu – đếm tần suất, tìm phần tử xuất hiện nhiều nhất.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/4/topic/2/",
            "html_file": "roadmap_data/topics/stage04_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    map<int,int> freq;
    for (int i = 0; i < n; i++) {
        int x; cin >> x;
        freq[x]++;
    }
    int val=-1, best=-1;
    for (auto [k,v] : freq)
        if (v > best) best=v, val=k;
    cout << "Gia tri xuat hien nhieu nhat: " << val << " (" << best << " lan)";
}""",
            "sample_py": """from collections import Counter
n = int(input())
a = list(map(int, input().split()))
c = Counter(a)
val, best = c.most_common(1)[0]
print("Gia tri xuat hien nhieu nhat:", val, "(", best, "lan)")"""
        },
        {
            "title": "4.3. Xử lý dãy số & chuỗi dữ liệu",
            "summary": "Thao tác với dãy số – đảo ngược, xoay, tìm mẫu, phát hiện quy luật.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/4/topic/3/",
            "html_file": "roadmap_data/topics/stage04_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    reverse(a.begin(), a.end());
    for (int x : a) cout << x << " ";
}""",
            "sample_py": """n = int(input())
a = list(map(int, input().split()))
a.reverse()
print(*a)"""
        },
        {
            "title": "4.4. Bài toán mô phỏng thực tế",
            "summary": "Viết chương trình mô phỏng tình huống thực: điểm danh, bán hàng, quản lý dữ liệu đơn giản.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/4/topic/4/",
            "html_file": "roadmap_data/topics/stage04_topic04.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    map<string,int> sales;
    for (int i = 0; i < n; i++) {
        string name; int value;
        cin >> name >> value;
        sales[name] += value;
    }
    for (auto [k,v] : sales)
        cout << k << ": " << v << endl;
}""",
            "sample_py": """n = int(input())
sales = {}
for _ in range(n):
    name, val = input().split()
    val = int(val)
    sales[name] = sales.get(name, 0) + val
for k, v in sales.items():
    print(k + ":", v)"""
        },
    ],
}
