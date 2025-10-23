# oj/urls.py
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render

def home(request):
    stages = [
        ('Bắt đầu', 'Làm quen lập trình và tư duy logic cơ bản.', ['Nhập xuất', 'Vòng lặp', 'Điều kiện'], 'basic', 'sky'),
        ('Hai con trỏ', 'Tư duy tìm kiếm nhanh, tối ưu hoá dãy và mảng.', ['Hai con trỏ', 'Sliding Window', 'Prefix sum'], 'twopointers', 'indigo'),
        ('Cấu trúc dữ liệu', 'Hiểu và áp dụng các cấu trúc dữ liệu phổ biến.', ['Stack & Queue', 'Linked List', 'Set & Map'], 'datastructures', 'amber'),
        ('Thuật toán cơ bản', 'Các kỹ thuật tìm kiếm, sắp xếp, đệ quy.', ['Sort', 'Search', 'Recursion'], 'algorithms', 'emerald'),
        ('Đệ quy & Quay lui', 'Học cách chia nhỏ vấn đề và sinh nghiệm.', ['Quay lui', 'Nhánh cận', 'Sinh tổ hợp'], 'backtracking', 'pink'),
        ('Quy hoạch động', 'Tư duy tối ưu hóa bài toán phức tạp.', ['DP cơ bản', 'Knapsack', 'Dãy con tăng'], 'dp', 'purple'),
        ('Chia để trị', 'Kỹ thuật xử lý nhanh với chia nhỏ dữ liệu.', ['Merge sort', 'Binary search', 'Divide & conquer'], 'divideconquer', 'teal'),
        ('Đồ thị cơ bản', 'Làm quen với đỉnh, cạnh và các thuật toán duyệt.', ['DFS', 'BFS', 'Connected Components'], 'graph', 'orange'),
        ('Đồ thị nâng cao', 'Giải quyết các bài toán khó với Graph nâng cao.', ['Dijkstra', 'Floyd', 'Toposort'], 'graphadv', 'rose'),
        ('Cây & nhị phân', 'Nắm vững cây nhị phân và ứng dụng.', ['Tree traversal', 'Binary Search Tree', 'Segment Tree'], 'tree', 'green'),
        ('Cây nâng cao', 'Hiểu cấu trúc và ứng dụng cây phức tạp.', ['Fenwick Tree', 'HLD', 'Trie'], 'treeadv', 'lime'),
        ('Lý thuyết số', 'Các bài toán về chia hết, ước, modulo.', ['GCD/LCM', 'Modulo', 'Sieve of Eratosthenes'], 'math', 'cyan'),
        ('Chuỗi & Xử lý ký tự', 'Kỹ thuật thao tác chuỗi và pattern.', ['KMP', 'Hash String', 'Z-function'], 'string', 'fuchsia'),
        ('Nâng cao & Ứng dụng', 'Vận dụng tổng hợp và phát triển kỹ năng.', ['Bài thi', 'Tối ưu code', 'Phân tích độ phức tạp'], 'advanced', 'stone'),
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
