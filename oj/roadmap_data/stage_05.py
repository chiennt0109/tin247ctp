# path: oj/roadmap_data/stage_05.py

STAGE_5 = {
    "id": 5,
    "title": "🔁 Giai đoạn 5: Đệ quy & chia để trị",
    "summary": "Hiểu cách chia nhỏ bài toán và sử dụng lời gọi đệ quy để giải quyết hiệu quả hơn.",
    "topics": [
        {
            "title": "5.1. Đệ quy cơ bản",
            "summary": "Hiểu cơ chế gọi hàm lặp lại chính nó và cách dừng điều kiện cơ sở.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/5/topic/1/",
            "html_file": "roadmap_data/topics/stage05_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;

int factorial(int n) {
    if (n == 0 || n == 1) return 1; // Điều kiện dừng
    return n * factorial(n - 1);    // Gọi lại chính nó
}

int main() {
    int n; cin >> n;
    cout << factorial(n);
}""",
            "sample_py": """def factorial(n):
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)

n = int(input())
print(factorial(n))"""
        },
        {
            "title": "5.2. Chia để trị (Divide and Conquer)",
            "summary": "Phân tách bài toán thành các phần nhỏ hơn rồi kết hợp kết quả để tạo thành lời giải hoàn chỉnh.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/5/topic/2/",
            "html_file": "roadmap_data/topics/stage05_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;

int sumRange(vector<int>& a, int l, int r) {
    if (l == r) return a[l];
    int mid = (l + r) / 2;
    return sumRange(a, l, mid) + sumRange(a, mid + 1, r);
}

int main() {
    int n; cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    cout << sumRange(a, 0, n - 1);
}""",
            "sample_py": """def sum_range(a, l, r):
    if l == r:
        return a[l]
    m = (l + r) // 2
    return sum_range(a, l, m) + sum_range(a, m + 1, r)

n = int(input())
a = list(map(int, input().split()))
print(sum_range(a, 0, n - 1))"""
        },
        {
            "title": "5.3. Merge Sort & Quick Sort",
            "summary": "Hai ví dụ kinh điển của chia để trị – sắp xếp hiệu quả với độ phức tạp O(n log n).",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/5/topic/3/",
            "html_file": "roadmap_data/topics/stage05_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;

void merge(vector<int>& a, int l, int m, int r) {
    vector<int> L(a.begin() + l, a.begin() + m + 1);
    vector<int> R(a.begin() + m + 1, a.begin() + r + 1);
    int i = 0, j = 0, k = l;
    while (i < L.size() && j < R.size())
        a[k++] = (L[i] <= R[j]) ? L[i++] : R[j++];
    while (i < L.size()) a[k++] = L[i++];
    while (j < R.size()) a[k++] = R[j++];
}

void mergeSort(vector<int>& a, int l, int r) {
    if (l >= r) return;
    int m = (l + r) / 2;
    mergeSort(a, l, m);
    mergeSort(a, m + 1, r);
    merge(a, l, m, r);
}

int main() {
    int n; cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    mergeSort(a, 0, n - 1);
    for (int x : a) cout << x << " ";
}""",
            "sample_py": """def merge_sort(a):
    if len(a) <= 1:
        return a
    mid = len(a) // 2
    left = merge_sort(a[:mid])
    right = merge_sort(a[mid:])
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    result += left[i:] + right[j:]
    return result

print(*merge_sort(list(map(int, input().split()))))"""
        },
    ],
}
