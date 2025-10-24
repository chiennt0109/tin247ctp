# path: oj/views.py
from django.shortcuts import render
from django.http import JsonResponse
from judge.run_code import run_program
import os
# =============================
# DANH SÁCH GIAI ĐOẠN LUYỆN TẬP
# =============================
STAGES = [
    {
        "id": 1,
        "title": "Giai đoạn 1: Làm quen với thuật toán và cấu trúc cơ bản",
        "summary": "Khởi đầu hành trình với biến, vòng lặp, và tư duy thuật toán đơn giản. Giai đoạn này giúp bạn làm quen với cách phân tích bài toán và viết chương trình cơ bản.",
        "topics": [
            {
                "title": "1.1. Biến, kiểu dữ liệu và nhập xuất",
                "summary": "Hiểu cách khai báo biến, nhập và xuất dữ liệu trong C++ và Python.",
                "lang_support": ["C++", "Python"],
                "more_url": "/stages/1/topic/1",
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
                "lang_support": ["C++", "Python"],
                "more_url": "/stages/1/topic/2",
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
                "summary": "Tự động hoá các thao tác lặp, xử lý dãy số, tính tổng, đếm và nhiều hơn nữa.",
                "lang_support": ["C++", "Python"],
                "more_url": "/stages/1/topic/3",
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
            {
                "title": "1.4. Bài tập thực hành: Tổng các số chẵn",
                "summary": "Luyện tập viết vòng lặp, tính tổng có điều kiện, và xuất kết quả.",
                "lang_support": ["C++", "Python"],
                "more_url": "/stages/1/topic/4",
                "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, s = 0;
    cin >> n;
    for (int i = 1; i <= n; i++)
        if (i % 2 == 0) s += i;
    cout << s;
}""",
                "sample_py": """n = int(input())
print(sum(i for i in range(1, n + 1) if i % 2 == 0))"""
            },
        ],
    },
    # --- GIAI ĐOẠN 2..14 (KHUNG SẴN SÀNG MỞ RỘNG) ---
    {
        "id": 2,
        "title": "Giai đoạn 2: Mảng và chuỗi ký tự",
        "summary": "Làm quen với cấu trúc dữ liệu tuyến tính đầu tiên – mảng và chuỗi. Xử lý dữ liệu hàng loạt, đếm, tìm kiếm, đảo ngược, nối chuỗi, v.v.",
        "topics": [],
    },
    {"id": 3, "title": "Giai đoạn 3: Hàm và tư duy chia nhỏ bài toán", "summary": "", "topics": []},
    {"id": 4, "title": "Giai đoạn 4: Đệ quy và nguyên lý quay lui", "summary": "", "topics": []},
    {"id": 5, "title": "Giai đoạn 5: Cấu trúc dữ liệu ngăn xếp & hàng đợi", "summary": "", "topics": []},
    {"id": 6, "title": "Giai đoạn 6: Sắp xếp và tìm kiếm", "summary": "", "topics": []},
    {"id": 7, "title": "Giai đoạn 7: Mảng hai chiều và xử lý ma trận", "summary": "", "topics": []},
    {"id": 8, "title": "Giai đoạn 8: Kỹ thuật duyệt đồ thị (DFS/BFS)", "summary": "", "topics": []},
    {"id": 9, "title": "Giai đoạn 9: Quy hoạch động (Dynamic Programming)", "summary": "", "topics": []},
    {"id": 10, "title": "Giai đoạn 10: Chia để trị (Divide and Conquer)", "summary": "", "topics": []},
    {"id": 11, "title": "Giai đoạn 11: Tham lam (Greedy)", "summary": "", "topics": []},
    {"id": 12, "title": "Giai đoạn 12: Cấu trúc dữ liệu nâng cao (Set, Map, Heap...)", "summary": "", "topics": []},
    {"id": 13, "title": "Giai đoạn 13: Đồ thị có trọng số, cây khung, Dijkstra", "summary": "", "topics": []},
    {"id": 14, "title": "Giai đoạn 14: Ôn tập tổng hợp & các bài thi chuyên", "summary": "", "topics": []},
]
# ==========================================================
# 🌈 Trang chủ – Lộ trình học lập trình (14 giai đoạn)
# ==========================================================
def home(request):
    stages = [
        (
            "🧩 Giai đoạn 1: Làm quen với lập trình và tư duy máy tính",
            "Hiểu chương trình là gì, cách máy tính xử lý lệnh, và viết những lệnh đầu tiên.",
            ["Biến & kiểu dữ liệu", "Cấu trúc điều kiện & vòng lặp", "Nhập xuất cơ bản", "Bài tập tư duy logic cơ bản"],
            "basic",
            "sky",
        ),
        (
            "⚙️ Giai đoạn 2: Cấu trúc dữ liệu cơ bản & hàm",
            "Biết cách lưu trữ, truy cập và xử lý dữ liệu có cấu trúc; chia nhỏ chương trình thành các hàm.",
            ["Mảng 1D/2D", "Chuỗi ký tự", "Hàm – tham trị & tham chiếu", "Đọc & ghi file"],
            "data",
            "indigo",
        ),
        (
            "📊 Giai đoạn 3: Thuật toán cơ bản và độ phức tạp",
            "Hiểu bản chất của thuật toán, cách phân tích độ phức tạp và chọn giải pháp tối ưu hơn.",
            ["Tìm kiếm tuyến tính & nhị phân", "Sắp xếp cơ bản", "Độ phức tạp O(n), O(n log n)", "Đánh giá hiệu quả chương trình"],
            "algorithm",
            "emerald",
        ),
        (
            "🧠 Giai đoạn 4: Tư duy giải thuật & bài toán thực tế",
            "Áp dụng thuật toán vào các bài toán mô phỏng, thống kê, và xử lý dữ liệu.",
            ["Bài toán đếm & tính toán", "Thống kê & tìm kiếm dữ liệu", "Xử lý dãy số", "Bài toán mô phỏng logic"],
            "problem",
            "amber",
        ),
        (
            "🔁 Giai đoạn 5: Đệ quy & chia để trị",
            "Hiểu cách chia nhỏ bài toán và sử dụng lời gọi đệ quy để giải quyết.",
            ["Đệ quy cơ bản", "Gọi đệ quy lồng nhau", "Chia để trị", "Merge Sort & Quick Sort"],
            "recursion",
            "pink",
        ),
        (
            "📈 Giai đoạn 6: Quy hoạch động (Dynamic Programming)",
            "Tối ưu hóa bài toán bằng cách ghi nhớ trạng thái và kết quả trung gian.",
            ["Fibonacci tối ưu", "Knapsack", "LIS, LCS", "DP 2D & Bitmask DP"],
            "dp",
            "purple",
        ),
        (
            "🎯 Giai đoạn 7: Quay lui & nhánh cận (Backtracking)",
            "Duyệt toàn bộ không gian nghiệm và cắt tỉa nhánh không cần thiết để tối ưu thời gian.",
            ["Sinh tổ hợp, hoán vị", "N-Queens", "Sudoku", "Bài toán tổ hợp nâng cao"],
            "backtrack",
            "rose",
        ),
        (
            "🧱 Giai đoạn 8: Cấu trúc dữ liệu nâng cao",
            "Sử dụng các cấu trúc dữ liệu mạnh để tăng tốc độ xử lý và tối ưu lưu trữ.",
            ["Stack, Queue, Deque", "Linked List", "Set, Map, Heap", "Hash Table"],
            "datastruct",
            "teal",
        ),
        (
            "🌉 Giai đoạn 9: Đồ thị cơ bản",
            "Làm quen khái niệm đỉnh, cạnh, cách duyệt đồ thị và tìm liên thông.",
            ["Biểu diễn đồ thị", "DFS, BFS", "Connected Components", "Chu trình & cây khung"],
            "graph",
            "orange",
        ),
        (
            "🌍 Giai đoạn 10: Đồ thị nâng cao",
            "Học các thuật toán tìm đường, cây bao trùm nhỏ nhất và đồ thị có trọng số.",
            ["Dijkstra, Bellman-Ford", "Floyd–Warshall", "Toposort, Tarjan", "MST: Kruskal & Prim"],
            "graphadv",
            "green",
        ),
        (
            "🌲 Giai đoạn 11: Cây & cấu trúc đặc biệt",
            "Hiểu và sử dụng các loại cây để truy vấn & cập nhật dữ liệu nhanh chóng.",
            ["Binary Tree & BST", "AVL, Segment Tree", "Fenwick Tree", "Trie, Union-Find"],
            "tree",
            "lime",
        ),
        (
            "📐 Giai đoạn 12: Lý thuyết số và toán ứng dụng",
            "Vận dụng công cụ toán học trong lập trình để giải bài toán chia hết, modulo và tổ hợp.",
            ["GCD, LCM, Euclid mở rộng", "Modulo & nghịch đảo", "Sàng Eratosthenes", "Tổ hợp & phân tích số"],
            "math",
            "cyan",
        ),
        (
            "🔤 Giai đoạn 13: Chuỗi và xử lý văn bản",
            "Hiểu và áp dụng thuật toán chuỗi trong xử lý ký tự và so khớp mẫu.",
            ["KMP, Z-algorithm", "Rolling Hash", "Palindrome, Substring", "Pattern Matching"],
            "string",
            "fuchsia",
        ),
        (
            "🚀 Giai đoạn 14: Luyện thi & kỹ năng thi đấu",
            "Tổng hợp toàn bộ kiến thức, rèn tốc độ và tư duy phân tích để thi HSG hoặc chuyên Tin.",
            ["Bài tổng hợp (DP + Graph + Math)", "Phân tích bài nâng cao", "Tối ưu độ phức tạp", "Kỹ thuật debug & code sạch"],
            "advanced",
            "stone",
        ),
    ]
    return render(request, "home.html", {"stages": stages})
# 🌱 Trang chi tiết từng giai đoạn (VD: Giai đoạn 1)
def roadmap_stage(request, stage_id):
    """Trang chi tiết 1 giai đoạn"""
    stage = next((s for s in STAGES if s["id"] == stage_id), None)
    if not stage:
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy giai đoạn này."})

    # tìm prev / next
    idx = STAGES.index(stage)
    prev_stage = STAGES[idx - 1] if idx > 0 else None
    next_stage = STAGES[idx + 1] if idx < len(STAGES) - 1 else None

    context = {
        "stage": stage,
        "prev_stage": prev_stage,
        "next_stage": next_stage,
    }
    return render(request, "roadmap_stage.html", context)


def run_code_online(request):
    """Form chạy code trực tiếp trong trang"""
    if request.method == "POST":
        language = request.POST.get("language", "")
        code = request.POST.get("code", "")
        input_data = request.POST.get("input", "")
        try:
            output = run_program(language, code, input_data)
        except Exception as e:
            output = f"Lỗi khi chạy code: {str(e)}"
        return JsonResponse({"output": output})
    return JsonResponse({"error": "Invalid request"})
