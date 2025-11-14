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
            queryset = Event.objects.all()
        else:
            queryset = Event.objects.filter(
                Q(is_approved=True) | Q(created_by=request.user)
            )

        events = []
        for ev in queryset:
            bg = "#198754" if ev.is_approved else "#ffc107"
            events.append({
                "id": ev.id,
                "title": ev.name,
                "start": ev.start.isoformat(),
                "end": ev.end.isoformat(),
                "description": ev.description or "",
                "isApproved": ev.is_approved,
                "backgroundColor": bg,
                "borderColor": bg,
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

        if not title or not start_str or not end_str:
            return HttpResponseBadRequest("Missing required fields")

        # Safely parse ISO timestamps
        start_dt = parse_datetime(start_str)
        end_dt = parse_datetime(end_str)

        if not start_dt or not end_dt:
            return HttpResponseBadRequest("Invalid ISO datetime format")

        # Prevent overlapping only for normal users
        if not request.user.is_staff and is_overlapping(start_dt, end_dt):
            return JsonResponse(
                {"status": "error", "message": "This time slot is already booked."},
                status=409
            )

        auto_approve = request.user.is_staff

        event = Event.objects.create(
            name=title,
            start=start_dt,
            end=end_dt,
            description=description,
            created_by=request.user,
            is_approved=auto_approve,
            approved_at=now() if auto_approve else None,
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

        if not request.user.is_staff and is_overlapping(new_start, event.end, exclude_id=event.id):
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
    qs = Event.objects.filter(start__lt=end, end__gt=start, is_approved=True)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()