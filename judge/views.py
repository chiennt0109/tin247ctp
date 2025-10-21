from django.shortcuts import render
from django.http import JsonResponse
from .models import Problem, Submission

def health(_):
    return JsonResponse({"status": "ok"})

def problem_list(request):
    problems = list(Problem.objects.values("id","code","title"))
    return JsonResponse({"problems": problems})

def submission_list(request):
    subs = list(Submission.objects.values("id","problem__code","username","status"))
    return JsonResponse({"submissions": subs})
