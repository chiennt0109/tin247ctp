# path: oj/roadmap_data/stage_03.py

STAGE_3 = {
    "id": 3,
    "title": "📊 Giai đoạn 3: Thuật toán cơ bản và độ phức tạp",
    "summary": "Hiểu bản chất của thuật toán, cách phân tích độ phức tạp và chọn giải pháp tối ưu hơn.",
    "topics": [
        {
            "title": "3.1. Tìm kiếm tuyến tính & nhị phân",
            "summary": "Hiểu cách tìm kiếm phần tử trong mảng bằng Linear Search và Binary Search.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/3/topic/1/",
            "html_file": "roadmap_data/topics/stage03_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, x;
    cin >> n >> x;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    // Tìm kiếm tuyến tính
    int pos = -1;
    for (int i = 0; i < n; i++)
        if (a[i] == x) pos = i;

    if (pos != -1) cout << "Tim thay tai vi tri: " << pos;
    else cout << "Khong tim thay";
    return 0;
}""",
            "sample_py": """n, x = map(int, input().split())
a = list(map(int, input().split()))
if x in a:
    print("Tim thay tai vi tri:", a.index(x))
else:
    print("Khong tim thay")"""
        },
        {
            "title": "3.2. Các thuật toán sắp xếp cơ bản",
            "summary": "Cài đặt Selection Sort, Insertion Sort, Bubble Sort và hiểu độ phức tạp.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/3/topic/2/",
            "html_file": "roadmap_data/topics/stage03_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    // Bubble Sort
    for (int i = 0; i < n - 1; i++)
        for (int j = 0; j < n - i - 1; j++)
            if (a[j] > a[j + 1]) swap(a[j], a[j + 1]);

    for (int x : a) cout << x << " ";
    return 0;
}""",
            "sample_py": """n = int(input())
a = list(map(int, input().split()))
for i in range(n - 1):
    for j in range(n - i - 1):
        if a[j] > a[j + 1]:
            a[j], a[j + 1] = a[j + 1], a[j]
print(*a)"""
        },
        {
            "title": "3.3. Độ phức tạp thuật toán",
            "summary": "Phân biệt O(1), O(n), O(n log n), O(n²) và học cách chọn thuật toán tối ưu.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/3/topic/3/",
            "html_file": "roadmap_data/topics/stage03_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;

// Ví dụ O(n): tính tổng
long long sum_n(const vector<int>& a) {
    long long s = 0;
    for (int x : a) s += x;
    return s;
}

int main() {
    int n; cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    cout << "Tong = " << sum_n(a);
    return 0;
}""",
            "sample_py": """def sum_n(a):
    return sum(a)

n = int(input())
a = list(map(int, input().split()))
print("Tong =", sum_n(a))"""
        },
    ],
}
