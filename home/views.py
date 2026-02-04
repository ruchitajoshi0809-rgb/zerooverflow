from django.shortcuts import render
from .models import GarbageBin
from .ai_model import predict_overflow
from datetime import datetime

def dashboard(request):
    bins = GarbageBin.objects.all()

    for bin in bins:
        hours = (datetime.now() - bin.last_collected.replace(tzinfo=None)).seconds / 3600
        bin.overflow_risk = predict_overflow(bin.fill_level, hours)
        bin.save()

    return render(request, 'home/dashboard.html', {'bins': bins})
