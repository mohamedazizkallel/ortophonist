from django.shortcuts import render , get_object_or_404,redirect
from django.http import HttpResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required,user_passes_test
from django.contrib.auth.models import User
import random 



def home_view(request):
    return render(request,'website/home.html')

@user_passes_test(lambda u: u.is_superuser) 
def client_list_view(request):
    # Get all non-admin users
    clients = User.objects.filter(is_staff=False)
    return render(request, "website/client.html", {'clients': clients})


@login_required
def client_profile_view(request, user_id=None):
    user = request.user

    # 🧩 Case 1: Staff/Admin
    if user.is_staff or user.is_superuser:
        if user_id:
            client = get_object_or_404(User, id=user_id)
        else:
            # If staff visits /clients/profile/ without ID, redirect to list view
            return redirect('client_list')

    # 🧩 Case 2: Regular client
    else:
        # Client should always see their own profile
        if user_id and user_id != user.id:
            return redirect('my_profile')
        client = user

    # Example data for charts
    graph_data = [random.randint(1, 100) for _ in range(10)]
    bar_data_set = [
        [random.randint(10, 50) for _ in range(3)] for _ in range(10)
    ]

    return render(request, 'website/client_profile.html', {
        'client': client,
        'graph_data': graph_data,
        'bar_data_set': bar_data_set,
    })


