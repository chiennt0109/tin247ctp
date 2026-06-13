# path: oj/scratch.py
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse

SCRATCH_LESSONS = [
    {"number": 1, "slug": "bai-01", "file": "scratch_bai_01.html", "title": "Hãy để mình giới thiệu về Scratch!"},
    {"number": 2, "slug": "bai-02", "file": "scratch_bai_02.html", "title": "Hãy nhảy cùng thỏ Bashful!"},
    {"number": 3, "slug": "bai-03", "file": "scratch_bai_03.html", "title": "Tìm các bạn trong rừng!"},
    {"number": 4, "slug": "bai-04", "file": "scratch_bai_04.html", "title": "Chuyến đi dành cho thỏ Bashful!"},
    {"number": 5, "slug": "bai-05", "file": "scratch_bai_05.html", "title": "Hãy tìm nhà của mèo Scratch!"},
    {"number": 6, "slug": "bai-06", "file": "scratch_bai_06.html", "title": "Hãy tìm ra con đường vượt các chướng ngại vật!"},
    {"number": 7, "slug": "bai-07", "file": "scratch_bai_07.html", "title": "Vượt qua khu rừng huyền bí!"},
    {"number": 8, "slug": "bai-08", "file": "scratch_bai_08.html", "title": "Vẽ tranh cùng mèo Scratch!"},
    {"number": 9, "slug": "bai-09", "file": "scratch_bai_09.html", "title": "Trang trí vườn hoa"},
    {"number": 10, "slug": "bai-10", "file": "scratch_bai_10.html", "title": "Trồng cây trong vườn"},
    {"number": 11, "slug": "bai-11", "file": "scratch_bai_11.html", "title": "Đi học đúng giờ"},
    {"number": 12, "slug": "bai-12", "file": "scratch_bai_12.html", "title": "Cuộc đua kỳ thú"},
    {"number": 13, "slug": "bai-13", "file": "scratch_bai_13.html", "title": "Chạy trốn con ma"},
]


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
