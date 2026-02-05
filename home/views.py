from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from .models import GarbageBin, Complaint  
from .ai_model import predict_overflow
from datetime import datetime
import json

# --- GOVERNMENT DASHBOARD VIEW ---
def dashboard(request):
    bins = GarbageBin.objects.all()

    # --- 1. NEW AUTO-FILL LOGIC (20 Days Cycle) ---
    for bin_obj in bins:
        try:
            # Calculate time passed since last cleaning
            time_diff = timezone.now() - bin_obj.last_emptied
            hours_passed = time_diff.total_seconds() / 3600
            
            # FORMULA: Fill to 100% over 20 Days (480 hours)
            # 100% / 480 hours = ~0.208% per hour
            new_fill_level = int(hours_passed * (100 / 480))
            
            # Cap at 100%
            bin_obj.fill_level = min(100, new_fill_level)
            
            # --- 2. NEW THRESHOLDS (75% and 90%) ---
            if bin_obj.fill_level >= 90:
                bin_obj.status = 'critical'
                bin_obj.overflow_risk = True
            elif bin_obj.fill_level >= 75:  # Changed to 75%
                bin_obj.status = 'warning'
                bin_obj.overflow_risk = False
            else:
                bin_obj.status = 'safe'
                bin_obj.overflow_risk = False
                
            bin_obj.save()
        except Exception as e:
            pass

    # --- COUNTS ---
    total_count = bins.count()
    safe_count = bins.filter(status='safe').count()
    warning_count = bins.filter(status='warning').count()
    critical_count = bins.filter(status='critical').count()

    # --- ALERTS ---
    critical_bins = bins.filter(status='critical')
    pending_complaints = Complaint.objects.filter(status='pending').order_by('-created_at')
    
    # --- TASK COUNTS ---
    all_complaints = Complaint.objects.all().order_by('-created_at')
    progress_count = Complaint.objects.filter(status='acknowledged').count()
    resolved_count = Complaint.objects.filter(status='resolved').count()

    return render(request, 'home/dashboard.html', {
        'bins': bins,
        'recent_complaints': all_complaints,
        'pending_complaints': pending_complaints,
        'critical_bins': critical_bins,
        'total_count': total_count,
        'safe_count': safe_count,
        'warning_count': warning_count,
        'critical_count': critical_count,
        'progress_count': progress_count,
        'resolved_count': resolved_count
    })
# --- COMPLAINT SUBMISSION VIEW ---
from django.contrib import messages  # <--- IMPORT THIS
from django.shortcuts import render, redirect

def complaint(request):
    if request.method == 'POST':
        complaint_type = request.POST.get('complaint_type')
        location = request.POST.get('location')
        description = request.POST.get('description')
        
        Complaint.objects.create(
            complaint_type=complaint_type,
            location=location,
            description=description,
            status='pending',
            gov_notified=False
        )

        # ✅ SUCCESS MESSAGE
        messages.success(request, "✅ Complaint Submitted Successfully! The authorities have been notified.")
        
        return redirect('gov_dashboard')

    return render(request, 'home/complaint.html')
# --- API VIEWS (Keep as is) ---
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
            return JsonResponse({'success': True, 'complaint_id': complaint.id, 'message': 'Complaint submitted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

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

def get_gov_alerts(request):
    recent_complaints = Complaint.objects.filter(gov_notified=False, status='pending').order_by('-created_at')
    critical_bins = GarbageBin.objects.filter(overflow_risk=True)
    alerts = []
    
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
        complaint.gov_notified = True
        complaint.save()

    for bin in critical_bins:
        alerts.append({
            'type': 'bin_overflow',
            'title': f'🚨 Bin Overflow Risk: {bin.location}',
            'message': f'Fill level: {bin.fill_level}%',
            'details': f'Last collected: {bin.last_emptied.strftime("%Y-%m-%d %H:%M")}',
            'bin_id': bin.id,
            'timestamp': timezone.now().isoformat(),
            'priority': 'critical'
        })

    return JsonResponse({'alerts': alerts})
from django.shortcuts import get_object_or_404, redirect

# Add this new view function to handle the "Mark Complete" button
def resolve_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    complaint.status = 'resolved'
    complaint.gov_notified = True
    complaint.save()
    return redirect('dashboard')
# --- PASTE THIS AT THE VERY BOTTOM OF home/views.py ---

from django.shortcuts import get_object_or_404, redirect

def update_complaint_status(request, complaint_id, status_type):
    # Get the specific complaint
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    # Check which button was clicked
    if status_type == 'progress':
        complaint.status = 'acknowledged'  # Set to In Progress
        complaint.gov_notified = True      # Mark as seen
    elif status_type == 'resolved':
        complaint.status = 'resolved'      # Set to Completed
        complaint.gov_notified = True      # Mark as seen
        
    complaint.save()
    return redirect('dashboard') # Go back to dashboard