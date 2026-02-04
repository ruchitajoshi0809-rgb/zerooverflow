from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('complaint/', views.complaint, name='complaint'),
    path('api/submit-complaint/', views.submit_complaint_api, name='submit_complaint_api'),
    path('api/recent-complaints/', views.get_recent_complaints, name='recent_complaints'),
    path('api/gov-alerts/', views.get_gov_alerts, name='gov_alerts'),
]
