from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.db import models
from .models import CustomUser, Role

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'role')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'is_superuser')

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'role', 'manager', 'no_manager', 'is_staff', 'is_active')
    list_filter = ('role', 'no_manager', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('role', 'no_manager', 'manager', 'additional_managers', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'role', 'no_manager', 'manager', 'additional_managers', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('last_name', 'first_name', 'email')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit manager choices to only staff and superusers
        if db_field.name == "manager":
            kwargs["queryset"] = CustomUser.objects.filter(
                models.Q(is_superuser=True) | 
                models.Q(role__name__in=['admin', 'staff'])
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # Limit additional managers choices to only staff and superusers
        if db_field.name == "additional_managers":
            kwargs["queryset"] = CustomUser.objects.filter(
                models.Q(is_superuser=True) | 
                models.Q(role__name__in=['admin', 'staff'])
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

class RoleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Role, RoleAdmin)
