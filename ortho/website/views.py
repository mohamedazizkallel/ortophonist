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


def client_profile_view(request, user_id):
    client = get_object_or_404(User, id=user_id)

    # Example graph data for the line chart
    graph_data = [random.randint(1, 100) for _ in range(10)]  # 10 random values

    # Generate dummy bar data (3 metrics for each of the line chart points)
    bar_data_set = [
        [random.randint(10, 50) for _ in range(3)] for _ in range(10)  # 10 sets of 3 random metrics
    ]

    return render(request, 'website/client_profile.html', {
        'client': client,
        'graph_data': graph_data,
        'bar_data_set': bar_data_set,  # Pass it to the template
    })

@login_required
def profile_redirect_view(request):
    return redirect('client_profile', user_id=request.user.id)  # Use 'client_profile' name