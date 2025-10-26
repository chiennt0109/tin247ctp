# path: problems/ai_helper.py
"""
Module giả lập tầng AI gợi ý, debug, gợi ý bài tiếp theo.
Hiện có thể hoạt động offline, không cần OpenAI key.
Nếu sau này bạn muốn dùng API thật, chỉ cần sửa phần gen_ai_response().
"""

import random

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
