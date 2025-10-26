# path: problems/ai/ai_hint.py
import random
import os
import requests

# 🧠 Dữ liệu gợi ý offline cơ bản
OFFLINE_HINTS = [
    "Hãy thử phân tích độ phức tạp của thuật toán bạn định dùng.",
    "Đôi khi sắp xếp dữ liệu trước sẽ giúp bài toán dễ hơn.",
    "Nếu kết quả sai, hãy kiểm tra kiểu dữ liệu (int/float).",
    "Sử dụng vòng lặp lồng nhau có thể gây timeout — thử tối ưu hơn.",
    "Hãy đọc kỹ đề: có thể có điều kiện biên đặc biệt bị bỏ sót."
]


def get_hint(problem_title: str, difficulty: str = "Easy"):
    """
    Trả về gợi ý cho bài toán dựa trên tiêu đề và độ khó.
    Ưu tiên: dùng HuggingFace API nếu có token, nếu không fallback về offline.
    """
    token = os.getenv("HF_TOKEN")  # token HuggingFace (nếu có)
    if not token:
        # ⚙️ Offline mode
        base_hint = random.choice(OFFLINE_HINTS)
        if difficulty == "Hard":
            base_hint += " (Hãy thử nghĩ đến chia để trị hoặc quy hoạch động.)"
        elif difficulty == "Medium":
            base_hint += " (Có thể dùng cấu trúc dữ liệu trung gian để tối ưu.)"
        return base_hint

    # 🚀 Online mode (nếu có token HuggingFace)
    prompt = f"Hãy cho gợi ý ngắn cho bài toán lập trình '{problem_title}'."
    try:
        resp = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": prompt},
            timeout=10
        )
        data = resp.json()
        if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()
        return random.choice(OFFLINE_HINTS)
    except Exception:
        return random.choice(OFFLINE_HINTS)
