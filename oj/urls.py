from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render

def home(request):
    stages = [
        ('Giai đoạn 1: Làm quen lập trình & tư duy thuật toán',
         'Bắt đầu làm quen với lập trình và tư duy máy tính.',
         ['Cấu trúc chương trình, biến, kiểu dữ liệu, điều kiện, vòng lặp, nhập xuất'],
         ['Hiểu cách máy tính xử lý lệnh', 'Viết được chương trình đơn giản', 'Hình thành tư duy thuật toán cơ bản'],
         'basic', 'sky'),

        ('Giai đoạn 2: Kỹ năng lập trình & xử lý dữ liệu',
         'Phát triển kỹ năng xử lý dữ liệu và tổ chức chương trình.',
         ['Mảng 1D/2D', 'Chuỗi ký tự', 'Hàm (truyền tham trị/tham chiếu)', 'Đọc/ghi file', 'Thống kê dữ liệu'],
         ['Xử lý dữ liệu có cấu trúc', 'Chia nhỏ bài toán thành hàm', 'Lưu trữ và truy xuất thông tin có hệ thống'],
         'data', 'indigo'),

        ('Giai đoạn 3: Thuật toán cơ bản',
         'Làm chủ các thuật toán nền tảng trong lập trình.',
         ['Tìm kiếm tuyến tính/nhị phân', 'Sắp xếp cơ bản (Selection/Insertion/Bubble/Quick/Merge)',
          'Đệ quy', 'Độ phức tạp', 'Chia để trị'],
         ['Thiết kế & cài đặt thuật toán', 'Đánh giá hiệu quả chương trình', 'Tối ưu cơ bản'],
         'algo', 'amber'),

        ('Giai đoạn 4: Cấu trúc dữ liệu nâng cao',
         'Nắm vững các cấu trúc dữ liệu quan trọng.',
         ['Stack', 'Queue/Deque', 'Linked List', 'Set/Map/Dictionary', 'Priority Queue/Heap', 'Hash Table'],
         ['Chọn cấu trúc dữ liệu phù hợp', 'Cài đặt & vận dụng vào bài toán thực tế', 'Phân biệt tuyến tính & phi tuyến tính'],
         'ds', 'emerald'),

        ('Giai đoạn 5: Thuật toán nâng cao',
         'Kỹ thuật giải bài toán tối ưu.',
         ['Quy hoạch động (DP: Knapsack, LIS, Count Ways)', 'Backtracking', 'Nhánh cận', 'Memoization', 'Chia để trị nâng cao'],
         ['Mô hình hóa trạng thái & chuyển trạng thái', 'Giảm độ phức tạp thời gian/không gian', 'Giải bài toán tối ưu hiệu quả'],
         'adv', 'pink'),

        ('Giai đoạn 6: Đồ thị và cây',
         'Cấu trúc đồ thị/cây và các thuật toán quan trọng.',
         ['Biểu diễn đồ thị (ma trận/danh sách kề)', 'DFS/BFS/Connected Components',
          'Dijkstra/Bellman-Ford/Floyd-Warshall', 'Tree/BST/LCA',
          'Segment Tree/Fenwick/Trie/Union-Find', 'Toposort/MST (Prim, Kruskal)/Euler'],
         ['Hiểu bản chất đồ thị/cây', 'Duyệt, tìm đường, phân tích quan hệ dữ liệu', 'Dùng cấu trúc cây xử lý bài phức tạp'],
         'graph', 'purple'),

        ('Giai đoạn 7: Lập trình chuyên nghiệp & tư duy thi đấu',
         'Tổng hợp & tối ưu hoá năng lực lập trình thuật toán.',
         ['OOP (C++/Java)', 'Bitmask', 'Binary Search on Answer', 'Greedy + DP', 'Tối ưu I/O', 'Debug & kiểm thử'],
         ['Viết chương trình tối ưu & rõ ràng', 'Kết hợp nhiều kỹ thuật trong một bài', 'Tư duy linh hoạt khi gặp bài mới'],
         'pro', 'stone'),
    ]

    return render(request, "home.html", {"stages": stages})

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("problems/", include("problems.urls")),
    path("submissions/", include("submissions.urls")),
    path("contests/", include("contests.urls")),
]
