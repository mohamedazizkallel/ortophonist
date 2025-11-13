from django.contrib import admin
from django.urls import path, include
from .views import home_view, client_list_view,client_profile_view

urlpatterns = [
    path('', home_view, name="home"),    
    path('clients/', client_list_view, name='client_list'), 
    path('clients/profile/', client_profile_view, name='client_profile_self'),  # For own profile
    path('clients/profile/<int:user_id>/', client_profile_view, name='client_profile'),  # For staff/admin
    
]