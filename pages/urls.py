from django.urls import path
from . import views

urlpatterns = [
    path('spotify-login/', views.spotify_login, name='spotify_login'),
    path('callback/', views.spotify_callback, name='spotify_callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('summary/', views.summary_page, name='summary'),
    path('spin-wheel/', views.spin_wheel, name='spin_wheel'),
]
