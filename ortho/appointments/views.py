from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from datetime import datetime
from .models import Event
import json


@login_required
def calendar_view(request):
    template = (
        "appointments/admin_calendar.html"
        if request.user.is_staff
        else "appointments/client_calendar.html"
    )
    return render(request, template)


@login_required
def get_events(request):

    # --------------------------------------------------------
    # GET: fetch events
    # --------------------------------------------------------
    if request.method == "GET":
        if request.user.is_staff:
            # Staff sees ALL events (approved and pending)
            queryset = Event.objects.all()
        else:
            # Regular users see:
            # 1. ALL approved events (to see blocked time slots)
            # 2. Their own pending events (to track their requests)
            queryset = Event.objects.filter(
                Q(is_approved=True) | Q(created_by=request.user)
            )

        events = []
        for ev in queryset:
            # Color coding: green for approved, yellow for pending
            bg = "#198754" if ev.is_approved else "#ffc107"
            
            # For non-staff users, hide sensitive info for other people's appointments
            if not request.user.is_staff and ev.is_approved and ev.created_by != request.user:
                # Show only that the slot is booked
                events.append({
                    "id": ev.id,
                    "title": "Booked",  # Generic title
                    "start": ev.start.isoformat(),
                    "end": ev.end.isoformat(),
                    "description": "",  # Hide description
                    "isApproved": ev.is_approved,
                    "backgroundColor": bg,
                    "borderColor": bg,
                    "extendedProps": {
                        "isOwnEvent": False,
                    }
                })
            else:
                # Staff or own events: show full details
                events.append({
                    "id": ev.id,
                    "title": ev.name,
                    "start": ev.start.isoformat(),
                    "end": ev.end.isoformat(),
                    "description": ev.description or "",
                    "isApproved": ev.is_approved,
                    "backgroundColor": bg,
                    "borderColor": bg,
                    "extendedProps": {
                        "isOwnEvent": ev.created_by == request.user,
                        "createdBy": ev.created_by.get_full_name() or ev.created_by.username,
                    }
                })

        return JsonResponse(events, safe=False)

    # --------------------------------------------------------
    # POST: create new event
    # --------------------------------------------------------
    elif request.method == "POST":

        # Parse JSON
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

        title = data.get("title") or data.get("name")
        start_str = data.get("start")
        end_str = data.get("end")
        description = data.get("description", "")
        user_id = data.get("user_id")  # For admin assignment
        auto_approve = data.get("auto_approve", False)

        if not title or not start_str or not end_str:
            return HttpResponseBadRequest("Missing required fields")

        # Safely parse ISO timestamps
        start_dt = parse_datetime(start_str)
        end_dt = parse_datetime(end_str)

        if not start_dt or not end_dt:
            return HttpResponseBadRequest("Invalid ISO datetime format")

        # Check for overlapping APPROVED appointments (for all users)
        if is_overlapping(start_dt, end_dt):
            return JsonResponse(
                {"status": "error", "message": "This time slot is already booked."},
                status=409
            )

        # Determine who the appointment is for
        if request.user.is_staff and user_id:
            # Admin is creating appointment for a specific user
            try:
                from django.contrib.auth.models import User
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": "User not found."},
                    status=404
                )
        else:
            # Regular user creating their own appointment
            target_user = request.user
            auto_approve = False  # Regular users can't auto-approve

        # Staff can choose to auto-approve
        should_approve = request.user.is_staff and auto_approve

        event = Event.objects.create(
            name=title,
            start=start_dt,
            end=end_dt,
            description=description,
            created_by=target_user,
            is_approved=should_approve,
            approved_at=now() if should_approve else None,
        )

        return JsonResponse(
            {
                "id": event.id,
                "title": event.name,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "description": event.description or "",
                "isApproved": event.is_approved,
            },
            status=201,
        )

    else:
        return HttpResponseBadRequest("Unsupported method")


@login_required
def update_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if not request.user.is_staff and event.created_by != request.user:
        return HttpResponseForbidden()

    if request.method not in ("PUT", "PATCH"):
        return HttpResponseBadRequest("Unsupported method")

    try:
        data = json.loads(request.body.decode("utf-8"))
    except:
        return HttpResponseBadRequest("Invalid JSON")

    title = data.get("title") or data.get("name")
    start_str = data.get("start")
    end_str = data.get("end")
    description = data.get("description")

    if title is not None:
        event.name = title

    if start_str is not None:
        new_start = parse_datetime(start_str)
        if not new_start:
            return HttpResponseBadRequest("Invalid start datetime")

        if is_overlapping(new_start, event.end, exclude_id=event.id):
            return JsonResponse({"error": "Timeslot unavailable"}, status=409)

        event.start = new_start

    if end_str is not None:
        new_end = parse_datetime(end_str)
        if not new_end:
            return HttpResponseBadRequest("Invalid end datetime")
        event.end = new_end

    if description is not None:
        event.description = description

    event.save()
    return JsonResponse({"status": "updated", "id": event.id})


@login_required
def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if not request.user.is_staff and event.created_by != request.user:
        return HttpResponseForbidden()

    if request.method != "DELETE":
        return HttpResponseBadRequest("Unsupported method")

    event.delete()
    return JsonResponse({"status": "deleted"})


@login_required
def approve_event(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    event = get_object_or_404(Event, pk=pk)
    
    # Check if approving this event would create an overlap
    if is_overlapping(event.start, event.end, exclude_id=event.id):
        return JsonResponse(
            {"status": "error", "message": "Cannot approve: time slot conflicts with another approved appointment."},
            status=409
        )
    
    event.is_approved = True
    event.approved_at = now()
    event.save()

    if event.created_by.email:
        send_mail(
            "Appointment Confirmed",
            f"Your appointment '{event.name}' on {event.start.strftime('%Y-%m-%d %H:%M')} has been approved.",
            settings.DEFAULT_FROM_EMAIL,
            [event.created_by.email],
            fail_silently=True,
        )

    return JsonResponse({"status": "approved", "id": event.id})


def is_overlapping(start, end, exclude_id=None):
    """
    Check if the given time slot overlaps with any APPROVED appointments.
    This ensures users can't book over already approved appointments.
    """
    qs = Event.objects.filter(start__lt=end, end__gt=start, is_approved=True)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()


@login_required
def get_users(request):
    """
    Return list of non-staff, non-admin users for admin to assign appointments.
    Only accessible by staff/admin.
    """
    if not request.user.is_staff:
        return HttpResponseForbidden("Only staff can access user list")
    
    from django.contrib.auth.models import User
    
    # Get all non-staff, non-superuser users
    users = User.objects.filter(is_staff=False, is_superuser=False).values(
        'id', 'username', 'first_name', 'last_name', 'email'
    )
    
    # Format the response
    user_list = []
    for user in users:
        full_name = f"{user['first_name']} {user['last_name']}".strip()
        if not full_name:
            full_name = user['username']
        
        user_list.append({
            'id': user['id'],
            'username': user['username'],
            'full_name': full_name,
            'email': user['email']
        })
    
    return JsonResponse(user_list, safe=False)