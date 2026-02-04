from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from .models import GarbageBin, Complaint  # Add Complaint import
from .ai_model import predict_overflow
from datetime import datetime
import json

def dashboard(request):
    bins = GarbageBin.objects.all()

    for bin in bins:
        hours = (datetime.now() - bin.last_collected.replace(tzinfo=None)).seconds / 3600
        bin.overflow_risk = predict_overflow(bin.fill_level, hours)
        bin.save()

    # Get recent complaints for dashboard
    recent_complaints = Complaint.objects.all().order_by('-created_at')[:5]
    
    return render(request, 'home/dashboard.html', {
        'bins': bins,
        'recent_complaints': recent_complaints
    })

# Make sure this function is properly indented (4 spaces)
def complaint(request):
    if request.method == 'POST':
        # Handle form submission
        complaint_type = request.POST.get('complaint_type')
        location = request.POST.get('location')
        description = request.POST.get('description')
        reported_by = request.POST.get('name', 'Anonymous')
        contact_info = request.POST.get('contact', '')
        
        # Create complaint
        complaint = Complaint.objects.create(
            complaint_type=complaint_type,
            location=location,
            description=description,
            reported_by=reported_by,
            contact_info=contact_info,
            status='pending'
        )
        
        # You could also create a notification for government here
        # For now, we'll just redirect with success message
        return render(request, 'home/complaint.html', {
            'success': True,
            'complaint_id': complaint.id
        })
    
    # GET request - show form
    return render(request, 'home/complaint.html')

# NEW: API endpoint for AJAX complaint submission
def submit_complaint_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            complaint = Complaint.objects.create(
                complaint_type=data.get('type'),
                location=data.get('location'),
                description=data.get('description'),
                reported_by=data.get('name', 'Anonymous'),
                contact_info=data.get('contact', ''),
                status='pending',
                gov_notified=False
            )
            
            # Create government notification (simplified)
            # In real app, this would create Notification objects
            
            return JsonResponse({
                'success': True,
                'complaint_id': complaint.id,
                'message': 'Complaint submitted successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

# NEW: Get complaints for dashboard (AJAX)
def get_recent_complaints(request):
    complaints = Complaint.objects.all().order_by('-created_at')[:10]
    data = []
    for complaint in complaints:
        data.append({
            'id': complaint.id,
            'type': complaint.get_complaint_type_display(),
            'location': complaint.location,
            'description': complaint.description[:100] + '...' if len(complaint.description) > 100 else complaint.description,
            'reported_by': complaint.reported_by,
            'status': complaint.status,
            'created_at': complaint.created_at.strftime('%Y-%m-%d %H:%M'),
            'status_class': 'badge-warning' if complaint.status == 'pending' else 'badge-success'
        })
    return JsonResponse({'complaints': data})

# NEW: Get government alerts (for gov dashboard)
def get_gov_alerts(request):
    # Get recent complaints that haven't been notified
    recent_complaints = Complaint.objects.filter(
        gov_notified=False,
        status='pending'
    ).order_by('-created_at')
    
    # Get bins with overflow risk
    critical_bins = GarbageBin.objects.filter(overflow_risk=True)
    
    alerts = []
    
    # Add complaint alerts
    for complaint in recent_complaints:
        alerts.append({
            'type': 'complaint',
            'title': f'New Complaint: {complaint.get_complaint_type_display()}',
            'message': f'Reported at {complaint.location}',
            'details': complaint.description[:200],
            'complaint_id': complaint.id,
            'timestamp': complaint.created_at.isoformat(),
            'priority': 'high'
        })
        # Mark as notified
        complaint.gov_notified = True
        complaint.save()
    
    # Add bin alerts
    for bin in critical_bins:
        alerts.append({
            'type': 'bin_overflow',
            'title': f'🚨 Bin Overflow Risk: {bin.location}',
            'message': f'Fill level: {bin.fill_level}%',
            'details': f'Last collected: {bin.last_collected.strftime("%Y-%m-%d %H:%M")}',
            'bin_id': bin.id,
            'timestamp': timezone.now().isoformat(),
            'priority': 'critical'
        })
    
    return JsonResponse({'alerts': alerts})