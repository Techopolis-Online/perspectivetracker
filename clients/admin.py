from django.contrib import admin
from .models import Client, ClientNote

class ClientNoteInline(admin.TabularInline):
    model = ClientNote
    extra = 1
    fields = ('title', 'content', 'author', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_name', 'email', 'point_of_contact')
    list_filter = ('point_of_contact',)
    search_fields = ('company_name', 'contact_name', 'email')
    inlines = [ClientNoteInline]

@admin.register(ClientNote)
class ClientNoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'author', 'created_at')
    list_filter = ('client', 'author')
    search_fields = ('title', 'content', 'client__company_name')
    readonly_fields = ('created_at', 'updated_at')
