from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Project URLs
    path('', views.project_list, name='project_list'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/update/', views.project_update, name='project_update'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
    
    # Project Type URLs
    path('types/', views.project_type_list, name='project_type_list'),
    path('types/create/', views.project_type_create, name='project_type_create'),
    path('types/<int:pk>/update/', views.project_type_update, name='project_type_update'),
    path('types/<int:pk>/delete/', views.project_type_delete, name='project_type_delete'),
    path('types/<int:pk>/status-choices/', views.project_type_status_choices, name='project_type_status_choices'),
    path('types/<int:pk>/milestone-choices/', views.project_type_milestone_choices, name='project_type_milestone_choices'),
    
    # Standard URLs
    path('standards/', views.standard_list, name='standard_list'),
    path('standards/<int:pk>/', views.standard_detail, name='standard_detail'),
    path('standards/create/', views.standard_create, name='standard_create'),
    path('standards/<int:pk>/update/', views.standard_update, name='standard_update'),
    path('standards/<int:pk>/delete/', views.standard_delete, name='standard_delete'),
    
    # Violation URLs
    path('standards/<int:standard_id>/violations/create/', views.violation_create, name='violation_create'),
    path('violations/<int:pk>/update/', views.violation_update, name='violation_update'),
    path('violations/<int:pk>/delete/', views.violation_delete, name='violation_delete'),
    
    # Project Violation URLs
    path('<int:project_id>/violations/create/', views.project_violation_create, name='project_violation_create'),
    path('violations/<int:pk>/update/', views.project_violation_update, name='project_violation_update'),
    path('violations/<int:pk>/delete/', views.project_violation_delete, name='project_violation_delete'),
    
    # Project Standard URLs
    path('<int:project_id>/standards/create/', views.project_standard_create, name='project_standard_create'),
    path('standards/<int:pk>/delete/', views.project_standard_delete, name='project_standard_delete'),
    
    # Page URLs
    path('<int:project_id>/pages/create/', views.page_create, name='page_create'),
    path('pages/<int:pk>/update/', views.page_update, name='page_update'),
    path('pages/<int:pk>/delete/', views.page_delete, name='page_delete'),
    
    # Milestone URLs
    path('<int:project_id>/milestones/create/', views.milestone_create, name='milestone_create'),
    path('milestones/<int:pk>/update/', views.milestone_update, name='milestone_update'),
    path('milestones/<int:pk>/delete/', views.milestone_delete, name='milestone_delete'),
] 