from django.urls import path
from .views import spotify_login, spotify_callback, spotify_summary

urlpatterns = [
    path('login/', spotify_login, name='spotify-login'),
    path('callback/', spotify_callback, name='spotify-callback'),
    path('summary/', spotify_summary, name='spotify-summary'),
]
