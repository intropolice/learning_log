from django.contrib import admin
from .models import Entry, Topic


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['text', 'owner', 'date_added']
    list_filter = ['owner', 'date_added']
    search_fields = ['text', 'owner__username']


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'topic', 'date_added']
    list_filter = ['date_added']
    search_fields = ['text', 'topic__text']
