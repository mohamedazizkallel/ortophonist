
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.utils.timezone import make_aware, now
from django.db.models import Q
from datetime import datetime
from .models import Event
import json


@login_required
def calendar_view(request):
    """
    Render the calendar page.

    - If the logged‑in user is a staff member (orthophonist / admin),
      we show the admin calendar.
    - Otherwise we show the client calendar.
    """
    template = "appointments/admin_calendar.html" if request.user.is_staff else "appointments/client_calendar.html"
    return render(request, template)


@login_required
def get_events(request):
    """
    GET  -> return a list of events as JSON for FullCalendar.
    POST -> create a new event (used by both admin & clients).

    Visibility rules
    ----------------
    * Admin / staff:
        - sees all events.
    * Client:
        - sees **their own** events (pending or approved)
        - plus all approved events, so they can see which slots are taken.
    """
    if request.method == "GET":
        if request.user.is_staff:
            queryset = Event.objects.all()
        else:
            queryset = Event.objects.filter(
                Q(is_approved=True) | Q(created_by=request.user)
            )

        events = []
        for ev in queryset:
            is_approved = ev.is_approved
            # Colors for FullCalendar (green = approved, yellow = pending)
            bg = "#198754" if is_approved else "#ffc107"
            border = bg

            events.append(
                {
                    "id": ev.id,
                    "title": ev.name,
                    "start": ev.start.isoformat(),
                    "end": ev.end.isoformat(),
                    "description": ev.description or "",
                    "isApproved": is_approved,
                    "backgroundColor": bg,
                    "borderColor": border,
                }
            )
        return JsonResponse(events, safe=False)

    if request.method == "POST":
        # Create a new event from JSON body
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

        try:
            start_dt = make_aware(datetime.fromisoformat(start_str))
            end_dt = make_aware(datetime.fromisoformat(end_str))
        except ValueError:
            return HttpResponseBadRequest("Invalid date format, expected ISO 8601")

        # If the creator is staff, the event is immediately approved.
        # For normal clients, the event is "pending" until the doctor approves it.
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

    return HttpResponseBadRequest("Unsupported HTTP method")


@login_required
def update_event(request, pk):
    """
    Update an existing event via PUT/PATCH.

    Only admins or the user who created the event are allowed
    to modify it.
    """
    event = get_object_or_404(Event, pk=pk)

    if not request.user.is_staff and event.created_by != request.user:
        return HttpResponseForbidden()

    if request.method not in ("PUT", "PATCH"):
        return HttpResponseBadRequest("Unsupported HTTP method")

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload")

    title = data.get("title") or data.get("name")
    start_str = data.get("start")
    end_str = data.get("end")
    description = data.get("description")

    if title is not None:
        event.name = title

    if start_str is not None:
        try:
            event.start = make_aware(datetime.fromisoformat(start_str))
        except ValueError:
            return HttpResponseBadRequest("Invalid start date format")

    if end_str is not None:
        try:
            event.end = make_aware(datetime.fromisoformat(end_str))
        except ValueError:
            return HttpResponseBadRequest("Invalid end date format")

    if description is not None:
        event.description = description

    event.save()

    return JsonResponse(
        {
            "id": event.id,
            "title": event.name,
            "start": event.start.isoformat(),
            "end": event.end.isoformat(),
            "description": event.description or "",
            "isApproved": event.is_approved,
        }
    )


@login_required
def delete_event(request, pk):
    """
    Delete an event.

    Only admins or the user who created the event can delete it.
    """
    event = get_object_or_404(Event, pk=pk)

    if not request.user.is_staff and event.created_by != request.user:
        return HttpResponseForbidden()

    if request.method != "DELETE":
        return HttpResponseBadRequest("Unsupported HTTP method")

    event.delete()
    return JsonResponse({"status": "deleted"})


@login_required
def approve_event(request, pk):
    """
    Admin approves a pending client request.

    This is called from the admin calendar when the doctor approves
    a requested appointment.
    """
    if not request.user.is_staff:
        return HttpResponseForbidden()

    event = get_object_or_404(Event, pk=pk)

    if request.method not in ("PATCH", "POST"):
        return HttpResponseBadRequest("Unsupported HTTP method")

    event.is_approved = True
    event.approved_at = now()
    event.save()

    return JsonResponse({"status": "approved"})
