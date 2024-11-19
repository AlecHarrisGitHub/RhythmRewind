"""
URL configuration for RhythmRewind project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from pages import views

urlpatterns = [
    path('accounts/spotify/login/callback/', views.spotify_callback, name='spotify_callback'),
    path('accounts/', include('allauth.urls')),
    path('delete_account/', views.delete_account, name='delete_account'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin/', admin.site.urls),
    path('generate_text/', views.generate_text, name='generate_text'),
    path('spotify/login/', views.spotify_login, name='spotify_login'),
    path('hangman/', views.hangman_game, name='hangman_game'),
]
