from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'users'
# Только используемые маршруты: сброс пароля без настроенной почты не объявляем.
urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
]
