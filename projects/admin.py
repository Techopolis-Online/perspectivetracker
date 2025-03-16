from django.contrib import admin
from .models import ProjectType, Project, Standard, Violation, ProjectViolation, ProjectStandard

@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'supports_standards', 'slug')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

class ProjectViolationInline(admin.TabularInline):
    model = ProjectViolation
    extra = 0
    fields = ('violation', 'status', 'assigned_to')
    raw_id_fields = ('violation', 'assigned_to')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'client', 'project_type', 'status')
    list_filter = ('status', 'project_type', 'client')
    search_fields = ('name', 'client__company_name')
    raw_id_fields = ('client', 'created_by')
    filter_horizontal = ('assigned_to',)
    date_hierarchy = 'created_at'
    inlines = [ProjectViolationInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']):
            return qs
        return qs.filter(assigned_to=request.user)

class ViolationInline(admin.TabularInline):
    model = Violation
    extra = 0
    fields = ('name',)

@admin.register(Standard)
class StandardAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description', 'version')
    raw_id_fields = ('created_by',)
    inlines = [ViolationInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin']):
            return qs
        return qs.none()
    
    def has_add_permission(self, request):
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'admin')
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'admin')
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'admin')

@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = ('name', 'standard')
    list_filter = ('standard', 'created_at')
    search_fields = ('name', 'description')
    raw_id_fields = ('standard', 'created_by')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin']):
            return qs
        return qs.none()
    
    def has_add_permission(self, request):
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'admin')
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'admin')
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'admin')

@admin.register(ProjectViolation)
class ProjectViolationAdmin(admin.ModelAdmin):
    list_display = ('project', 'violation', 'status', 'assigned_to', 'created_at')
    list_filter = ('status', 'created_at', 'project__project_type')
    search_fields = ('project__name', 'violation__name', 'notes', 'location')
    raw_id_fields = ('project', 'violation', 'created_by', 'assigned_to')
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']):
            return qs
        return qs.filter(project__assigned_to=request.user) | qs.filter(assigned_to=request.user)

@admin.register(ProjectStandard)
class ProjectStandardAdmin(admin.ModelAdmin):
    list_display = ('project', 'standard', 'created_at')
    list_filter = ('standard', 'project', 'created_at')
    search_fields = ('project__name', 'standard__name')
    raw_id_fields = ('project', 'standard', 'created_by')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin']):
            return qs
        return qs.filter(project__assigned_to=request.user)
    
    def has_add_permission(self, request):
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff'])
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff'])
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff'])
