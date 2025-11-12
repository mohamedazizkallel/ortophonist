from django.contrib import admin
from django.urls import path, include
from .views import home_view, client_list_view,client_profile_view,profile_redirect_view

urlpatterns = [
    path('', home_view, name="home"),    
    path('clients/', client_list_view, name='client_list'), 
    path('clients/profile/<int:user_id>/', client_profile_view, name='client_profile'),  # Change name to 'client_profile'     
    path('accounts/profile/', profile_redirect_view, name='profile_redirect'),  # Optional name for clarity
]