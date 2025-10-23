# path: app/views.py
from django.shortcuts import render
from judge.run_code import run_submission


# ==========================================================
# 🧩 Trang nộp bài
# ==========================================================
def submit_code(request):
    result = None
    if request.method == "POST":
        lang = request.POST.get("language")
        source = request.POST.get("source")
        result = run_submission(lang, source)
    return render(request, "submit.html", {"result": result})


# ==========================================================
# 🌈 Trang chủ – Lộ trình học lập trình 14 giai đoạn
# ==========================================================
def home(request):
    stages = [
        {"stage": "Làm quen với lập trình",
         "desc": "Hiểu chương trình là gì, viết lệnh đầu tiên, chạy và xem kết quả.",
         "examples": ['In "Hello World"', "Nhập & xuất dữ liệu"],
         "tag": "beginner", "color": "sky"},
        {"stage": "Cấu trúc điều khiển & tư duy logic",
         "desc": "Học If–Else, For, While, tư duy logic và thuật toán cơ bản.",
         "examples": ["If–Else, For, While", "Bài tập tính toán, mô phỏng"],
         "tag": "logic", "color": "indigo"},
        {"stage": "Cấu trúc dữ liệu cơ bản",
         "desc": "Làm quen mảng, chuỗi, danh sách, stack, queue, set, map.",
         "examples": ["Sắp xếp và tìm kiếm", "Ứng dụng stack và queue"],
         "tag": "datastruct", "color": "amber"},
        {"stage": "Hai con trỏ & cửa sổ trượt",
         "desc": "Giải bài toán tối ưu bằng hai con trỏ và kỹ thuật cửa sổ trượt.",
         "examples": ["Tìm cặp có tổng bằng X", "Đếm đoạn con hợp lệ"],
         "tag": "twopointers", "color": "teal"},
        {"stage": "Đệ quy & chia để trị",
         "desc": "Tư duy chia nhỏ vấn đề và giải quyết bằng đệ quy.",
         "examples": ["Đệ quy cơ bản", "Merge Sort, Quick Sort"],
         "tag": "recursion", "color": "pink"},
        {"stage": "Quy hoạch động (DP)",
         "desc": "Tối ưu hóa với trạng thái và bài toán con.",
         "examples": ["Dãy con tăng dài nhất", "Balo, chia mảnh"],
         "tag": "dp", "color": "purple"},
        {"stage": "Sinh & quay lui (Backtracking)",
         "desc": "Sinh nghiệm và tìm nghiệm thỏa điều kiện.",
         "examples": ["Liệt kê tổ hợp, hoán vị", "Giải Sudoku"],
         "tag": "backtrack", "color": "rose"},
        {"stage": "Đồ thị cơ bản",
         "desc": "Tìm hiểu đỉnh, cạnh và duyệt đồ thị.",
         "examples": ["DFS, BFS", "Đếm thành phần liên thông"],
         "tag": "graph", "color": "emerald"},
        {"stage": "Đồ thị nâng cao",
         "desc": "Áp dụng thuật toán đồ thị phức tạp hơn.",
         "examples": ["Dijkstra, Floyd–Warshall", "Toposort"],
         "tag": "graphadv", "color": "orange"},
        {"stage": "Cây & cấu trúc nhị phân",
         "desc": "Hiểu cấu trúc cây, duyệt và ứng dụng.",
         "examples": ["Duyệt cây nhị phân", "Binary Search Tree"],
         "tag": "tree", "color": "green"},
        {"stage": "Cây nâng cao",
         "desc": "Ứng dụng cây nâng cao để tối ưu truy vấn.",
         "examples": ["Segment Tree", "Fenwick Tree (BIT)"],
         "tag": "treeadv", "color": "lime"},
        {"stage": "Lý thuyết số",
         "desc": "Các bài toán toán học trong lập trình.",
         "examples": ["Ước, bội, modulo", "Thuật toán Euclid"],
         "tag": "math", "color": "cyan"},
        {"stage": "Chuỗi & xử lý ký tự",
         "desc": "Hiểu và áp dụng các thuật toán chuỗi.",
         "examples": ["KMP, Z-Function", "Hash String"],
         "tag": "string", "color": "fuchsia"},
        {"stage": "Nâng cao & thi đấu",
         "desc": "Tổng hợp và áp dụng trong các kỳ thi.",
         "examples": ["Tối ưu độ phức tạp", "Phân tích bài khó"],
         "tag": "advanced", "color": "stone"},
    ]
    return render(request, "home.html", {"stages": stages})
