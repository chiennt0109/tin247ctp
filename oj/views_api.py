# path: oj/views_api.py
from django.http import JsonResponse

def check_login(request):

    return JsonResponse({"is_authenticated": request.user.is_authenticated})
