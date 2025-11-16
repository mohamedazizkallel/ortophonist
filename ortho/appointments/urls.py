# In your calendar app's urls.py
from django.urls import path
from .views import get_events,update_event,calendar_view,delete_event,approve_event,get_users

urlpatterns = [
    path('', calendar_view, name='calendar'),
    path('events/all/', get_events, name='get_events'),
    path('events/update/<int:pk>/', update_event, name='update_event'),
    path('events/delete/<int:pk>/', delete_event, name='delete_event'),
    path('events/approve/<int:pk>/', approve_event, name='approve_event'),
    path('users/', get_users, name='get_users'),  # NEW: Add this line
]