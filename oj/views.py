from django.shortcuts import render
from judge.run_code import run_submission

def submit_code(request):
    result = None
    if request.method == "POST":
        lang = request.POST.get("language")
        source = request.POST.get("source")
        result = run_submission(lang, source)
    return render(request, "submit.html", {"result": result})
