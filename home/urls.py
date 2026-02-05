from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('complaint/', views.complaint, name='complaint'),
    path('api/submit-complaint/', views.submit_complaint_api, name='submit_complaint_api'),
    path('api/recent-complaints/', views.get_recent_complaints, name='recent_complaints'),
    path('api/gov-alerts/', views.get_gov_alerts, name='gov_alerts'),
    path('resolve-complaint/<int:complaint_id>/', views.resolve_complaint, name='resolve_complaint'),
    path('update-status/<int:complaint_id>/<str:status_type>/', views.update_complaint_status, name='update_status'),
]
