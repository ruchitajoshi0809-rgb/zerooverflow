from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from .models import GarbageBin, Complaint  
from .ai_model import predict_overflow
from datetime import datetime
import json


def dashboard(request):
    bins = GarbageBin.objects.all()

    # Calculate overflow risk for each bin
    for bin in bins:
        hours = (timezone.now() - bin.last_emptied).total_seconds() / 3600
        bin.overflow_risk = predict_overflow(bin.fill_level, hours)
        bin.save()

    # Dashboard counts
    total_count = bins.count()
    safe_count = bins.filter(status='safe').count()
    warning_count = bins.filter(status='warning').count()
    critical_count = bins.filter(status='critical').count()

    recent_complaints = Complaint.objects.all().order_by('-created_at')[:5]

    return render(request, 'home/dashboard.html', {
        'bins': bins,
        'recent_complaints': recent_complaints,
        'total_count': total_count,
        'safe_count': safe_count,
        'warning_count': warning_count,
        'critical_count': critical_count,
    })


def complaint(request):
    if request.method == 'POST':
        complaint_type = request.POST.get('complaint_type')
        location = request.POST.get('location')
        description = request.POST.get('description')
        reported_by = request.POST.get('name', 'Anonymous')
        contact_info = request.POST.get('contact', '')
        
        complaint = Complaint.objects.create(
            complaint_type=complaint_type,
            location=location,
            description=description,
            reported_by=reported_by,
            contact_info=contact_info,
            status='pending'
        )

        return render(request, 'home/complaint.html', {
            'success': True,
            'complaint_id': complaint.id
        })

    return render(request, 'home/complaint.html')


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
    recent_complaints = Complaint.objects.filter(
        gov_notified=False,
        status='pending'
    ).order_by('-created_at')

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
