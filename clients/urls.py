from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_list, name='client_list'),
    path('create/', views.client_create, name='client_create'),
    path('<int:pk>/', views.client_detail, name='client_detail'),
    path('<int:pk>/update/', views.client_update, name='client_update'),
    path('<int:pk>/delete/', views.client_delete, name='client_delete'),
    path('<int:client_pk>/note/create/', views.note_create, name='note_create'),
    path('note/<int:pk>/', views.note_detail, name='note_detail'),
    path('note/<int:pk>/update/', views.note_update, name='note_update'),
    path('note/<int:pk>/delete/', views.note_delete, name='note_delete'),
    
    # Co-worker related URLs
    path('coworker/<int:pk>/delete/', views.coworker_delete, name='coworker_delete'),
    path('coworker/<int:pk>/update/', views.coworker_update, name='coworker_update'),
    path('coworker/<int:pk>/resend/', views.resend_invitation, name='resend_invitation'),
    path('invitation/<str:token>/', views.accept_invitation, name='accept_invitation'),
] 