from django.urls import path
from .views import gov_dashboard

urlpatterns = [
    path('dashboard/', gov_dashboard, name='gov_dashboard'),
]
