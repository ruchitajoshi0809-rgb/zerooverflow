from django.shortcuts import render

from home.models import GarbageBin

def gov_dashboard(request):
    alerts = GarbageBin.objects.filter(overflow_risk=True)
    return render(request, 'government/gov_dashboard.html', {'alerts': alerts})

