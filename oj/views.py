# path: oj/views.py
from django.shortcuts import render


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
