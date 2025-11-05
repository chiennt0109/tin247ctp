# path: problems/ai_helper.py
"""
Module giả lập tầng AI gợi ý, debug, gợi ý bài tiếp theo.
Hiện có thể hoạt động offline, không cần OpenAI key.
Nếu sau này bạn muốn dùng API thật, chỉ cần sửa phần gen_ai_response().
"""

import random
from problems.models import Problem, UserProgress
from submissions.models import Submission

# ======================
# 🧠 AI Hint Generator
# ======================
def gen_ai_hint(statement: str, difficulty: str) -> str:
    hint_bank = [
        "Thử bắt đầu bằng việc đọc kỹ ràng buộc và xác định độ phức tạp cần thiết.",
        "Nếu bài có nhiều truy vấn, hãy nghĩ đến cấu trúc dữ liệu như Segment Tree hoặc Fenwick.",
        "Với bài tìm đường, BFS/DFS thường là hướng đi đầu tiên.",
        "Nếu bài có từ khóa 'dãy con dài nhất', hãy nghĩ đến Quy hoạch động (DP).",
        "Khi gặp lỗi tràn số, hãy chuyển sang kiểu long long hoặc int64.",
        "Thử chạy test nhỏ bằng tay và kiểm tra biến bị reset chưa."
    ]
    base = random.choice(hint_bank)
    return f"[Gợi ý cho bài {difficulty}] {base}"


# ======================
# 🧩 AI Debug Explanation
# ======================
def analyze_failed_test(input_data: str, expected: str, got: str) -> str:
    if got.strip() == "":
        return "Chương trình của bạn không in ra kết quả nào. Hãy kiểm tra phần xuất dữ liệu."
    if got.strip() == expected.strip():
        return "Kết quả đúng rồi, có thể lỗi xảy ra ở test khác."
    if len(got) > len(expected):
        return "Kết quả bạn in ra nhiều hơn mong đợi — có thể quên xuống dòng hoặc debug print."
    if len(got) < len(expected):
        return "Kết quả thiếu — có thể vòng lặp chưa duyệt hết dữ liệu."
    return "Hãy so sánh từng dòng giữa output và expected để tìm khác biệt nhỏ (dấu cách, xuống dòng, v.v.)."


# ======================
# 🚀 AI Recommend Next Problem
# ======================
def recommend_next(difficulty: str) -> str:
    recs = {
        "Easy": "Thử sang bài 'SUMSEQ' hoặc 'BASICLOOP' để luyện thêm kỹ năng cơ bản.",
        "Medium": "Bạn có thể thử 'SORTSTR' hoặc 'BINSEARCH' để rèn kỹ năng thuật toán trung bình.",
        "Hard": "Hãy thử 'GRAPHMST' hoặc 'DPBOX' để chinh phục mức cao hơn!"
    }
    return recs.get(difficulty, "Không rõ độ khó — hãy chọn bài phù hợp với khả năng của bạn.")
# ======================
# 🎯 AI Learning Path
# ======================
def build_learning_path(user, solved_count: int, avg_difficulty: str):
    """
    Sinh gợi ý lộ trình học miễn phí (offline logic).
    """
    plan = []

    if solved_count < 3:
        plan.append("🔰 Làm quen: tập trung vào các bài Easy để nắm cú pháp và vòng lặp.")
        plan.append("👉 Học các chủ đề: nhập xuất, điều kiện, vòng lặp.")
    elif avg_difficulty == "Easy":
        plan.append("⚡ Bạn đã làm quen tốt! Hãy chuyển sang mức Medium.")
        plan.append("👉 Học thêm: mảng, chuỗi, hàm, tìm kiếm tuần tự.")
    elif avg_difficulty == "Medium":
        plan.append("🚀 Bạn đang ở mức trung cấp. Hãy luyện thêm các bài về sắp xếp và quy hoạch động.")
        plan.append("👉 Gợi ý: 'SORTARR', 'DPFIB', 'MAXSUMSUB'")
    else:
        plan.append("🌟 Rất tốt! Bạn có thể thử các bài Hard về đồ thị, cây, hoặc tối ưu hóa.")
        plan.append("👉 Ví dụ: 'MSTPATH', 'FLOWMAX', 'BITSEG'")
    
    return {
        "summary": f"Lộ trình dành cho {user.username if user else 'bạn'}",
        "recommendations": plan
    }

# 🚀 AI Recommend dựa theo hồ sơ người dùng
def recommend_next_personal(user):
    """
    Gợi ý bài tiếp theo dựa vào tiến trình học (UserProgress + Submission).
    """
    if not user.is_authenticated:
        return "🔒 Bạn cần đăng nhập để nhận gợi ý cá nhân hóa."

    # 1️⃣ Lấy toàn bộ bài đã làm
    solved = Submission.objects.filter(user=user, verdict="Accepted").values_list("problem__id", flat=True)
    total = solved.count()

    if total == 0:
        # Người mới -> bắt đầu Easy
        easy = Problem.objects.filter(difficulty="Easy").order_by("?").first()
        return f"🔰 Bạn chưa làm bài nào. Hãy thử bắt đầu với bài **{easy.title}** (mức Easy)."

    # 2️⃣ Tính độ khó trung bình đã làm
    probs = Problem.objects.filter(id__in=solved)
    diff_level = {"Easy": 1, "Medium": 2, "Hard": 3}
    avg = sum(diff_level[p.difficulty] for p in probs) / len(probs)

    # 3️⃣ Chọn mức gợi ý kế tiếp
    if avg < 1.5:
        next_diff = "Medium"
    elif avg < 2.5:
        next_diff = "Hard"
    else:
        next_diff = "Hard"

    # 4️⃣ Gợi ý bài chưa làm trong mức đó
    next_prob = (
        Problem.objects.filter(difficulty=next_diff)
        .exclude(id__in=solved)
        .order_by("?")
        .first()
    )

    if not next_prob:
        return "🎉 Bạn đã hoàn thành hầu hết các bài trong mức này! Thử quay lại luyện tập các chủ đề yếu hơn nhé."

    return f"🎯 Dựa trên tiến trình của bạn, hãy thử bài **{next_prob.title}** (mức {next_diff})."
