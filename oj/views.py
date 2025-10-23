from django.shortcuts import render

def home(request):
    stages = [
        ("Giai đoạn 1️⃣: Làm quen lập trình & tư duy máy tính",
         "Hiểu cách máy tính hoạt động, viết chương trình đầu tiên và nắm tư duy thuật toán cơ bản.",
         ["Cấu trúc chương trình", "Biến & kiểu dữ liệu", "Nhập xuất cơ bản", "Điều kiện, vòng lặp"],
         "beginner", "sky"),

        ("Giai đoạn 2️⃣: Làm quen ngôn ngữ lập trình (C++, Python, Java)",
         "Làm chủ cú pháp, nhập xuất, hàm, mảng và chuỗi trong ngôn ngữ lập trình.",
         ["Hàm & tham số", "Chuỗi ký tự", "Mảng 1D/2D", "File I/O"],
         "language", "indigo"),

        ("Giai đoạn 3️⃣: Kỹ năng giải thuật cơ bản",
         "Làm quen với tư duy thuật toán, chia bài toán thành bước nhỏ và viết chương trình giải quyết.",
         ["Bài toán liệt kê", "Đếm, tính tổng, tối đa/tối thiểu", "Tìm kiếm tuyến tính & nhị phân"],
         "algorithm", "emerald"),

        ("Giai đoạn 4️⃣: Sắp xếp và phân tích độ phức tạp",
         "Hiểu các thuật toán sắp xếp và đánh giá hiệu năng chương trình.",
         ["Bubble, Insertion, Selection, Merge, Quick Sort", "Độ phức tạp O(n), O(n log n)", "Phân tích thời gian chạy"],
         "sort", "amber"),

        ("Giai đoạn 5️⃣: Cấu trúc dữ liệu cơ bản",
         "Tìm hiểu và ứng dụng các cấu trúc dữ liệu nền tảng.",
         ["Stack, Queue, Deque", "Linked List", "Set, Map", "Hash Table"],
         "datastruct", "teal"),

        ("Giai đoạn 6️⃣: Đệ quy & Chia để trị",
         "Hiểu cách chia nhỏ bài toán, gọi lại chính mình và tối ưu hóa qua mô hình đệ quy.",
         ["Đệ quy cơ bản", "Chia để trị", "Quicksort, Mergesort", "Tìm kiếm nhị phân mở rộng"],
         "recursion", "pink"),

        ("Giai đoạn 7️⃣: Quy hoạch động (Dynamic Programming)",
         "Tư duy lưu trữ trạng thái, giải quyết bài toán tối ưu bằng quy hoạch động.",
         ["Fibonacci tối ưu", "Knapsack", "LIS (Dãy con tăng dài nhất)", "DP 2D, Bitmask DP"],
         "dp", "purple"),

        ("Giai đoạn 8️⃣: Quay lui và sinh (Backtracking & Generation)",
         "Sinh nghiệm, duyệt toàn bộ không gian nghiệm, ứng dụng trong bài tổ hợp, Sudoku, hoán vị.",
         ["Sinh tổ hợp, hoán vị", "N-Queens", "Sudoku", "Tìm tất cả nghiệm"],
         "backtrack", "rose"),

        ("Giai đoạn 9️⃣: Đồ thị cơ bản",
         "Hiểu khái niệm đỉnh, cạnh và cách duyệt đồ thị.",
         ["Biểu diễn đồ thị", "DFS, BFS", "Connected Components", "Chu trình & cây khung"],
         "graph", "orange"),

        ("Giai đoạn 🔟: Đồ thị nâng cao",
         "Nâng cao kỹ năng xử lý đồ thị, tìm đường, cây bao trùm nhỏ nhất.",
         ["Dijkstra, Bellman-Ford", "Floyd-Warshall", "Toposort", "MST: Kruskal, Prim"],
         "graphadv", "green"),

        ("Giai đoạn 11️⃣: Cây & Cấu trúc dữ liệu nâng cao",
         "Sử dụng cây và cấu trúc nâng cao để tối ưu hóa thuật toán.",
         ["Cây nhị phân, BST, AVL", "Segment Tree, Fenwick Tree", "Union-Find, Trie"],
         "tree", "lime"),

        ("Giai đoạn 12️⃣: Lý thuyết số & Toán trong lập trình",
         "Trang bị công cụ toán học để xử lý các bài toán số học và thuật toán.",
         ["Ước chung lớn nhất (GCD)", "Modulo", "Phân tích thừa số", "Sàng Eratosthenes"],
         "math", "cyan"),

        ("Giai đoạn 13️⃣: Chuỗi & Xử lý ký tự",
         "Áp dụng kỹ thuật xử lý chuỗi để giải quyết bài toán văn bản và pattern matching.",
         ["KMP, Z-Algorithm", "Rolling Hash", "Palindrome, Substring", "Pattern matching"],
         "string", "fuchsia"),

        ("Giai đoạn 14️⃣: Luyện thi & dự án tổng hợp",
         "Rèn luyện kỹ năng thi HSG, OI, hoặc phỏng vấn lập trình với bài tổng hợp đa kỹ thuật.",
         ["Bài tổng hợp (DP + Graph)", "Tối ưu độ phức tạp", "Lập trình hướng đối tượng", "Phân tích & debug"],
         "advanced", "stone"),
    ]

    return render(request, "home.html", {"stages": stages})
