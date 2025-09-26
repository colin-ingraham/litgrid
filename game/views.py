from django.shortcuts import render

# Create your views here.
def daily(request):
    return render(request, "game/daily.html")