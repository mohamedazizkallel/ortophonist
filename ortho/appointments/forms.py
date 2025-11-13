from django import forms
from .models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'start', 'end']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Appointment name'}),
            'start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
