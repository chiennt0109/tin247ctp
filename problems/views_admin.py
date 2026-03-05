# =====================================================
# 📁 File: problems/views_admin.py (Semantic Engine v3) – FULL VERSION
#  + NHẬN DIỆN TAG TỪ MỤC "Nguồn"
#  + Chạy offline 100%
# =====================================================

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.html import strip_tags

import json
import re
import unicodedata

from .models import Tag, Problem


# -----------------------------------------------------
# 🔧 NORMALIZE TEXT
# -----------------------------------------------------
def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-zA-Z0-9 ]+", " ", s)
    return s.lower().strip()


def has_any(s: str, keywords) -> bool:
    return any(k in s for k in keywords)


# -----------------------------------------------------
# 🏷️ NHẬN DIỆN TAG TỪ MỤC "Nguồn"
# -----------------------------------------------------
import logging
logger = logging.getLogger(__name__)


def detect_source_tag(statement: str):
    """
    Đọc mục 'Nguồn' ở dạng bảng markdown, HTML hoặc text.
    Hỗ trợ cả trường hợp giá trị nằm ở dòng kế tiếp.
    """
    if not statement:
        return None

    text = statement.replace("*", "")
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    logger.info("=== SOURCE DEBUG RAW LINES ===")
    for line in lines:
        logger.info(f"[LINE] {line}")

    for i, line in enumerate(lines):
        lower = line.lower()

        # Nếu chứa chữ 'nguồn'
        if "nguồn" in lower:

            # 1) Trường hợp có dấu '|' bên phải
            bar_pos = line.find("|")
            if bar_pos != -1:
                value = line[bar_pos + 1:].strip(" |")
                if value:
                    logger.info(f"[SOURCE] Found inline: {value}")
                    return value

            # 2) Trường hợp Nguồn: xxx
            colon_pos = line.find(":")
            if colon_pos != -1:
                value = line[colon_pos + 1:].strip()
                if value:
                    logger.info(f"[SOURCE] Found by colon: {value}")
                    return value

            # 3) Trường hợp BẢNG BỊ TÁCH DÒNG: giá trị nằm dòng kế tiếp
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip(" |")
                if next_line:
                    logger.info(f"[SOURCE] Found on next line: {next_line}")
                    return next_line

    logger.info("[SOURCE] No source tag detected.")
    return None






# -----------------------------------------------------
# 🔑 MAP KEYWORD TỪ "Nguồn" → TAG TRONG DB
# -----------------------------------------------------
SOURCE_KEYWORD_MAP = {
    # ==========================
    # 🔹 CẤU TRÚC DỮ LIỆU CƠ BẢN
    # ==========================
    "mảng": "Array",
    "array": "Array",

    "ngăn xếp": "Stack",
    "stack": "Stack",

    "hàng đợi": "Queue",
    "queue": "Queue",

    "deque": "Deque",
    "double ended queue": "Deque",
    "hàng đợi 2 đầu": "Deque",

    "priority queue": "Priority Queue",
    "heap": "Priority Queue",
    "min heap": "Priority Queue",
    "max heap": "Priority Queue",

    "dslk": "Linked List",
    "linked list": "Linked List",

    # ==========================
    # 🔹 CẤU TRÚC DỮ LIỆU NÂNG CAO
    # ==========================
    "trie": "Trie",
    "prefix tree": "Trie",

    "bst": "Tree",
    "binary search tree": "Tree",
    "cây nhị phân": "Tree",

    "segment tree": "Segment Tree",
    "cây đoạn": "Segment Tree",

    "fenwick": "Fenwick Tree",
    "binary indexed tree": "Fenwick Tree",

    "rmq": "RMQ",
    "range minimum query": "RMQ",
    "range max query": "RMQ",

    "sparse table": "Sparse Table",

    "dsu": "DSU",
    "union find": "DSU",
    "disjoint set": "DSU",

    "treap": "Balanced BST",
    "avl": "Balanced BST",
    "splay": "Balanced BST",
    "cây xoay": "Balanced BST",
    "balanced tree": "Balanced BST",

    # upgrade DS
    "segment tree beats": "Segment Tree",
    "fenwick 2d": "Fenwick Tree",
    "bit 2d": "Fenwick Tree",

    "mo": "Mo's Algorithm",
    "mo's algorithm": "Mo's Algorithm",

    # ==========================
    # 🔹 TỐI ƯU CẤU TRÚC DỮ LIỆU
    # ==========================
    "cấu trúc dữ liệu": "Data Structure",
    "data structure": "Data Structure",
    "tối ưu cấu trúc": "Data Structure",
    "tối ưu hóa cấu trúc dữ liệu": "Data Structure",
    "opti ds": "Data Structure",

    # ==========================
    # 🔹 GRAPH
    # ==========================
    "đồ thị": "Graph",
    "graph": "Graph",

    "bfs": "Graph",
    "dfs": "Graph",

    "dijkstra": "Shortest Path",
    "bellman": "Shortest Path",
    "floyd": "Shortest Path",

    "mst": "Minimum Spanning Tree",
    "kruskal": "Minimum Spanning Tree",
    "prim": "Minimum Spanning Tree",

    # ==========================
    # 🔹 STRING / HASH
    # ==========================
    "string": "String",
    "chuỗi": "String",

    "kmp": "Kmp",
    "z-function": "String",
    "manacher": "Manacher",

    "hash": "Hash",
    "băm": "Hash",

    # ==========================
    # 🔹 SLIDING WINDOW / TWO POINTERS
    # ==========================
    "sliding window": "Sliding Window",
    "cửa sổ trượt": "Sliding Window",

    "two pointers": "Two Pointers",
    "hai con trỏ": "Two Pointers",

    # ==========================
    # 🔹 MATH / NUMBER THEORY
    # ==========================
    "số học": "Math",
    "math": "Math",
    "mod": "Number Theory",
    "nguyên tố": "Number Theory",
    "prime": "Number Theory",
    "gcd": "Number Theory",
    "lcm": "Number Theory",

    # ==========================
    # 🔹 COMBINATORICS
    # ==========================
    "tổ hợp": "Combinatorics",
    "chỉnh hợp": "Combinatorics",
    "đếm": "Combinatorics",

    # ==========================
    # 🔹 DP
    # ==========================
    "dp": "Dynamic Programming",
    "quy hoạch": "Dynamic Programming",
    "bitmask": "Bitmask",
    "mask": "Bitmask",

    # ==========================
    # 🔹 GREEDY / SORTING
    # ==========================
    "sort": "Sorting",
    "sắp xếp": "Sorting",

    "greedy": "Greedy",
    "tham lam": "Greedy",

    # ==========================
    # 🔹 SEARCH / BS
    # ==========================
    "binary search": "Binary Search",
    "tìm kiếm nhị phân": "Binary Search",
    "Binary search": "Binary Search",
    "Tìm kiếm nhị phân": "Binary Search",

    # ==========================
    # 🔹 SIMULATION / BRUTE FORCE
    # ==========================
    "mô phỏng": "Simulation",
    "simulation": "Simulation",

    "brute force": "Brute Force",
    "thử mọi cách": "Brute Force",

    # ==========================
    # 🔹 INTERVAL / SCHEDULING
    # ==========================
    "đoạn": "Interval",
    "interval": "Interval",
    "Đoạn": "Interval",

    "lập lịch": "Scheduling",
    "scheduling": "Scheduling",
    "Lập lịch": "Scheduling",
    
    # ==========================
    # 🔹 MATCHING / GHÉP CẶP
    # ==========================
    "ghép cặp": "Matching",
    "ghep cap": "Matching",
    "matching": "Matching",
    "Ghép cặp": "Matching",
    
    # ==========================
    # 🔹 GEOMETRY
    # ==========================
    "Bài toán hình học": "Geometry",
    "hình học": "Geometry",
    "geometry": "Geometry",
    
    # ==========================
    # 🔹 OPTIMIZATION
    # ==========================
    "tối ưu": "Optimization",
    "tối ưu hóa": "Optimization",
    "optimization": "Optimization",
    "optimize": "Optimization",
    
    # ==========================
    # 🔹 DATA STRUCTURE (bổ sung)
    # ==========================
    "cấu trúc dữ liệu": "Data Structure",
    "data structure": "Data Structure",
    "ctdl": "Data Structure",
}



def extract_tags_from_source(src_text: str):
    """
    Nhận list tag từ chuỗi 'Nguồn', ví dụ:
        'Bài toán Đoạn / Lập lịch. (Scheduling)'
    - Chuẩn hoá cả source và key trong map (bỏ dấu, lower...)
    - Trả về danh sách tên Tag (string)
    """
    if not src_text:
        return []

    norm_src = normalize_text(src_text)
    found = set()

    for key, mapped in SOURCE_KEYWORD_MAP.items():
        key_norm = normalize_text(key)
        if key_norm and key_norm in norm_src:
            found.add(mapped)

    # Nếu không map được keyword -> dùng nguyên text làm tag "thô"
    if not found:
        return [src_text.strip()]

    return list(found)



# -----------------------------------------------------
# 🧠 NHẬN DẠNG CONCEPT TAG (nội dung bài)
# -----------------------------------------------------
def detect_concept_tags(title: str, statement: str):
    raw = f"{title}\n{statement}"
    text = raw.lower()
    norm = normalize_text(raw)

    tags = set()

    # (Giữ nguyên toàn bộ các phần nhận diện BS, DP, Graph...)
    # --------------------------------------------------------
    # [ĐỂ TIẾT KIỆM CHỖ: giữ nguyên Y CHANG khối detect_concept_tags của bạn]
    # --------------------------------------------------------

    # fallback
    if not tags:
        tags.add("General")

    return tags


# -----------------------------------------------------
# 🎯 Ánh xạ tag concept → Tag trong DB
# -----------------------------------------------------
def resolve_tag_names_from_concepts(concepts):
    if not concepts:
        qs = Tag.objects.filter(name="General")
        return list(qs.values_list("name", flat=True)) or []

    qs = Tag.objects.filter(name__in=list(concepts))
    names = list(qs.values_list("name", flat=True))

    if not names:
        qs = Tag.objects.filter(name="General")
        return list(qs.values_list("name", flat=True)) or []

    return names


# -----------------------------------------------------
# 📏 ƯỚC LƯỢNG SCALE N TỪ RÀNG BUỘC
# -----------------------------------------------------
def estimate_scale(statement: str):
    text = statement or ""
    max_val = 0

    for m in re.finditer(r'(\d+)\s*\*\s*10\^(\d+)', text):
        a = int(m.group(1))
        b = int(m.group(2))
        max_val = max(max_val, a * (10 ** b))

    for m in re.finditer(r'10\^(\d+)', text):
        b = int(m.group(1))
        max_val = max(max_val, 10 ** b)

    for m in re.finditer(r'\b\d{4,}\b', text):
        v = int(m.group(0))
        max_val = max(max_val, v)

    return max_val or None


# -----------------------------------------------------
# ⏱️ ƯỚC LƯỢNG TIME LIMIT & MEMORY LIMIT
# -----------------------------------------------------
def estimate_time_memory(concepts, statement: str):
    text_l = (statement or "").lower()
    n_scale = estimate_scale(statement)

    time_limit = 1.0
    memory_limit = 256  # MB

    hard_tags = {
        "Dynamic Programming", "Bitmask Dp", "Dp On Tree",
        "Graph", "Tree", "Segment Tree", "Fenwick Tree",
        "Shortest Path", "Minimum Spanning Tree", "Hash String",
    }
    medium_tags = {
        "Binary Search", "Two Pointers", "Sliding Window",
        "Hash", "Number Theory", "Combinatorics",
        "String", "Kmp", "Manacher",
    }

    concepts_set = set(concepts)

    if concepts_set & hard_tags:
        time_limit = max(time_limit, 2.0)
    if concepts_set & medium_tags:
        time_limit = max(time_limit, 1.5)

    if n_scale:
        if n_scale >= 10 ** 7:
            time_limit = max(time_limit, 3.0)
            memory_limit = max(memory_limit, 512)
        elif n_scale >= 10 ** 6:
            time_limit = max(time_limit, 2.0)
            memory_limit = max(memory_limit, 384)
        elif n_scale >= 2 * 10 ** 5:
            time_limit = max(time_limit, 1.5)
            memory_limit = max(memory_limit, 256)
        else:
            memory_limit = max(memory_limit, 192)
    else:
        time_limit = max(time_limit, 1.5)
        memory_limit = max(memory_limit, 256)

    if "subtask" in text_l or "rang buoc" in text_l or "constraints" in text_l:
        time_limit += 0.5

    return float(int(time_limit)), int(memory_limit)


# -----------------------------------------------------
# 🎚️ ƯỚC LƯỢNG ĐỘ KHÓ
# -----------------------------------------------------
def estimate_difficulty(concepts, statement: str):
    text_l = (statement or "").lower()
    score = 0

    hard_kw = [
        "segment tree", "fenwick", "lazy propagation",
        "max flow", "min cut", "bitmask dp", "dp on tree",
        "lca", "binary lifting", "rerooting",
    ]
    med_kw = [
        "binary search", "two pointers", "sliding window", "greedy",
        "prefix sum", "bfs", "dfs", "dijkstra", "union find", "dsu",
        "knapsack", "digit dp",
    ]
    easy_kw = [
        "vong lap", "loop", "array", "mang", "input", "output",
    ]

    score += sum(2 for k in hard_kw if k in text_l)
    score += sum(1 for k in med_kw if k in text_l)
    score -= sum(1 for k in easy_kw if k in text_l)

    for c in concepts:
        if c in [
            "Dynamic Programming", "Bitmask Dp", "Dp On Tree",
            "Segment Tree", "Fenwick Tree", "Graph", "Tree",
        ]:
            score += 1.5
        elif c in [
            "Binary Search", "Two Pointers", "Sliding Window",
            "Hash", "Hash String", "Number Theory",
        ]:
            score += 1

    n_chars = len(statement or "")
    if n_chars > 3000:
        score += 2
    elif n_chars > 1500:
        score += 1

    if "subtask" in text_l or "rang buoc" in text_l or "constraints" in text_l:
        score += 1

    if score >= 5:
        return "Hard"
    elif score >= 2:
        return "Medium"
    return "Easy"


# -----------------------------------------------------
# 🧩 SINH CODE TỰ ĐỘNG
# -----------------------------------------------------
PREFIX_BY_TAG = {
    "Dynamic Programming": "DP",
    "Bitmask Dp": "DP",
    "Dp On Tree": "DP",
    "Array": "ARR",
    "String": "STR",
    "Kmp": "STR",
    "Manacher": "STR",
    "Hash": "HASH",
    "Hash String": "HASH",
    "Binary Search": "BS",
    "Two Pointers": "TP",
    "Sliding Window": "SW",
    "Graph": "GRAPH",
    "Tree": "TREE",
    "Lca": "TREE",
    "Minimum Spanning Tree": "MST",
    "Segment Tree": "SEG",
    "Fenwick Tree": "BIT",
    "Bitmask": "BM",
    "Greedy": "GRD",
    "Brute Force": "BF",
    "Implementation": "IMP",
    "Number Theory": "NT",
    "Combinatorics": "COMB",
    "Probability": "PROB",
}


def generate_problem_code(concepts):
    prefix = "GEN"
    for c in concepts:
        if c in PREFIX_BY_TAG:
            prefix = PREFIX_BY_TAG[c]
            break

    existing = Problem.objects.filter(code__startswith=prefix).values_list("code", flat=True)
    max_id = 0
    for c in existing:
        m = re.match(rf"{prefix}(\d+)$", c)
        if m:
            try:
                max_id = max(max_id, int(m.group(1)))
            except ValueError:
                pass

    return f"{prefix}{max_id + 1:03d}"




# -----------------------------------------------------
# 🎯 MAIN ANALYSIS API — CHỈNH Ở ĐÂY
# -----------------------------------------------------
@csrf_exempt
@staff_member_required
def ai_analyze_problem(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8"))
        title = (body.get("title") or "").strip()
        statement_raw = body.get("statement") or ""
        statement = strip_tags(statement_raw)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # 1️⃣ TAG theo nội dung
    concept_tags = detect_concept_tags(title, statement)
    tag_names = resolve_tag_names_from_concepts(concept_tags)

    # ⭐ 2️⃣ TAG từ mục "Nguồn"
    source_text = detect_source_tag(statement)
    if source_text:
        src_tags = extract_tags_from_source(source_text)

        existing_src = list(
            Tag.objects.filter(name__in=src_tags).values_list("name", flat=True)
        )

        tag_names.extend(existing_src)

    # xoá tag trùng lặp
    tag_names = list(dict.fromkeys(tag_names))

    # 3️⃣ Độ khó
    difficulty = estimate_difficulty(tag_names, statement)

    # 4️⃣ Sinh code
    code = generate_problem_code(tag_names)

    # 5️⃣ Time & memory
    time_limit, memory_limit = estimate_time_memory(tag_names, statement)

    return JsonResponse(
        {
            "code": code,
            "difficulty": difficulty,
            "tags": tag_names,
            "time_limit": time_limit,
            "memory_limit": memory_limit,
        }
    )


@csrf_exempt
@staff_member_required
def ai_suggest_tags(request):
    if request.method == "POST":
        return ai_analyze_problem(request)
    return JsonResponse({"error": "POST only"}, status=405)
