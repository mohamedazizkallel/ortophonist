from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

class Event(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField("Title", max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField()
    description = models.TextField(blank=True, null=True) 
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "events"
        ordering = ["start"]

    def __str__(self):
        return f"{self.name} ({'Approved' if self.is_approved else 'Pending'})"
    
class Availability(models.Model):
    weekday = models.IntegerField(choices=[(i, datetime.strftime(datetime.strptime(str(i), "%w"), "%A")) for i in range(7)])
    start_time = models.TimeField()
    end_time = models.TimeField()

