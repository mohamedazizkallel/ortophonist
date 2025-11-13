
from django.urls import path
from . import views

urlpatterns = [
    # Calendar main view
    path('', views.calendar_view, name='calendar'),

    # REST‑like JSON API used by the JavaScript calendar
    # GET  /calendar/events/all/  -> list events
    # POST /calendar/events/add/  -> create new event
    # (Both routes are mapped to the same view for backwards compatibility.)
    path('events/all/', views.get_events, name='get_events'),
    path('events/add/', views.get_events, name='add_event'),

    # Update / delete / approve operations
    path('events/update/<int:pk>/', views.update_event, name='update_event'),
    path('events/delete/<int:pk>/', views.delete_event, name='delete_event'),
    path('events/approve/<int:pk>/', views.approve_event, name='approve_event'),
]
