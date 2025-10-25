# path: oj/roadmap_data/stage_01.py

STAGE_1 = {
    "id": 1,
    "title": "Giai đoạn 1: Làm quen với thuật toán và cấu trúc cơ bản",
    "summary": "Khởi đầu hành trình với biến, vòng lặp, và tư duy thuật toán đơn giản.",
    "topics": [
        {
            "title": "1.1. Biến, kiểu dữ liệu và nhập xuất",
            "summary": "Hiểu cách khai báo biến, nhập và xuất dữ liệu trong C++ và Python.",
            "more_url": "/stages/1/topic/1/",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int a, b;
    cin >> a >> b;
    cout << a + b << endl;
    return 0;
}""",
            "sample_py": """a, b = map(int, input().split())
print(a + b)"""
        },
        {
            "title": "1.2. Cấu trúc điều kiện (if / else)",
            "summary": "Phân nhánh quyết định trong chương trình – nền tảng cho mọi thuật toán phức tạp.",
            "more_url": "/stages/1/topic/2/",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    if (n % 2 == 0) cout << "Even";
    else cout << "Odd";
}""",
            "sample_py": """n = int(input())
print("Even" if n % 2 == 0 else "Odd")"""
        },
        {
            "title": "1.3. Vòng lặp for / while",
            "summary": "Tự động hoá thao tác lặp, xử lý dãy số, tính tổng, đếm, kiểm tra điều kiện lặp.",
            "more_url": "/stages/1/topic/3/",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, sum = 0; cin >> n;
    for (int i = 1; i <= n; i++) sum += i;
    cout << sum;
}""",
            "sample_py": """n = int(input())
print(sum(range(1, n + 1)))"""
        },
    ],
}
