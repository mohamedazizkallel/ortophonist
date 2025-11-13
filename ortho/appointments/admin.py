from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'start', 'end', 'is_approved', 'approved_at')
    list_filter = ('is_approved', 'start')
    search_fields = ('name', 'created_by__username')
    ordering = ('-start',)
    actions = ['approve_selected_events']

    @admin.action(description="Approve selected events")
    def approve_selected_events(self, request, queryset):
        count = queryset.update(is_approved=True, approved_at=None)
        self.message_user(request, f"{count} event(s) approved successfully.")
