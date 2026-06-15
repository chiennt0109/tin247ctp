# path: oj/scratch.py
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse

SCRATCH_LESSONS = [
    {"number": 1, "slug": "bai-01", "file": "scratch_bai_01.html", "title": "Hãy để mình giới thiệu về Scratch!"},
    {"number": 2, "slug": "bai-02", "file": "scratch_bai_02.html", "title": "Hãy nhảy cùng thỏ Bashful!"},
    {"number": 3, "slug": "bai-03", "file": "scratch_bai_03.html", "title": "Gọi bạn trong khu rừng xanh!"},
    {"number": 4, "slug": "bai-04", "file": "scratch_bai_04.html", "title": "Hành trình qua ba miền kỳ thú!"},
    {"number": 5, "slug": "bai-05", "file": "scratch_bai_05.html", "title": "Robot Miu tìm trạm năng lượng!"},
    {"number": 6, "slug": "bai-06", "file": "scratch_bai_06.html", "title": "Tàu Zumi vượt mê cung sao băng!"},
    {"number": 7, "slug": "bai-07", "file": "scratch_bai_07.html", "title": "Chim Moka vượt vườn ánh sáng!"},
    {"number": 8, "slug": "bai-08", "file": "scratch_bai_08.html", "title": "Bút Pico vẽ bức tranh hình vuông!"},
    {"number": 9, "slug": "bai-09", "file": "scratch_bai_09.html", "title": "Ong Kiki trang trí vườn Hoa Sao!"},
    {"number": 10, "slug": "bai-10", "file": "scratch_bai_10.html", "title": "Robot Bimo trồng vườn năng lượng!"},
    {"number": 11, "slug": "bai-11", "file": "scratch_bai_11.html", "title": "Đồng hồ Kiko giúp Bin đến lớp đúng giờ!"},
    {"number": 12, "slug": "bai-12", "file": "scratch_bai_12.html", "title": "Giải đua Robot Mini và bảng xếp hạng!"},
    {"number": 13, "slug": "bai-13", "file": "scratch_bai_13.html", "title": "Drone Nari tránh vệ tinh tuần tra!"},
    {"number": 14, "slug": "bai-14", "file": "scratch_bai_14.html", "title": "Toán tiểu học trong Scratch"},
]

SCRATCH_SUB_LESSONS = {
    ("bai-14", "toan-01"): {"file": "scratch_bai_14_01_phep_tinh_bieu_thuc.html", "title": "Phép tính và biểu thức"},
    ("bai-14", "toan-02"): {"file": "scratch_bai_14_02_chan_le_chia_het.html", "title": "Chẵn lẻ và chia hết"},
    ("bai-14", "toan-03"): {"file": "scratch_bai_14_03_so_nguyen_to_chinh_phuong.html", "title": "Số nguyên tố và số chính phương"},
    ("bai-14", "toan-04"): {"file": "scratch_bai_14_04_uoc_boi_chia_nhom.html", "title": "Ước, bội và chia nhóm"},
    ("bai-14", "toan-05"): {"file": "scratch_bai_14_05_day_so_quy_luat.html", "title": "Dãy số và quy luật"},
    ("bai-14", "toan-06"): {"file": "scratch_bai_14_06_tong_dem_theo_dieu_kien.html", "title": "Tổng, đếm theo điều kiện"},
    ("bai-14", "toan-07"): {"file": "scratch_bai_14_07_phan_so_ti_so_phan_tram.html", "title": "Phân số, tỉ số, phần trăm"},
    ("bai-14", "toan-08"): {"file": "scratch_bai_14_08_chu_vi_dien_tich.html", "title": "Chu vi và diện tích"},
    ("bai-14", "toan-09"): {"file": "scratch_bai_14_09_ve_hinh_but_ve.html", "title": "Vẽ hình bằng bút vẽ"},
    ("bai-14", "toan-10"): {"file": "scratch_bai_14_10_toa_do_luoi_di_chuyen.html", "title": "Tọa độ, lưới và di chuyển"},
    ("bai-14", "toan-11"): {"file": "scratch_bai_14_11_thoi_gian_dong_ho.html", "title": "Thời gian, đồng hồ và lịch"},
    ("bai-14", "toan-12"): {"file": "scratch_bai_14_12_bai_toan_loi_van.html", "title": "Bài toán lời văn"},
}


def _topic_file(filename):
    return Path(settings.BASE_DIR) / "oj" / "roadmap_data" / "topics" / filename


def _render_topic_file(filename):
    path = _topic_file(filename)
    if not path.exists():
        raise Http404("Không tìm thấy nội dung Scratch.")
    return HttpResponse(path.read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")


def scratch_home(request):
    return _render_topic_file("scratch.html")


def scratch_lesson(request, lesson_slug):
    lesson = next((item for item in SCRATCH_LESSONS if item["slug"] == lesson_slug), None)
    if lesson is None:
        raise Http404("Không tìm thấy bài Scratch.")
    return _render_topic_file(lesson["file"])


def scratch_sub_lesson(request, lesson_slug, sub_slug):
    lesson = SCRATCH_SUB_LESSONS.get((lesson_slug, sub_slug))
    if lesson is None:
        raise Http404("Không tìm thấy bài Scratch.")
    return _render_topic_file(lesson["file"])
