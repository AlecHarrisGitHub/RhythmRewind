from django.shortcuts import redirect, render
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.http import HttpResponse
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os

def spotify_login(request):
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv('SPOTIFY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
        scope="user-read-playback-state user-library-read"
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

def spotify_callback(request):
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv('SPOTIFY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
    )
    code = request.GET.get('code')
    token_info = sp_oauth.get_access_token(code)

    if token_info:
        sp = Spotify(auth=token_info['access_token'])
        profile_data = sp.current_user()
        username = profile_data['id']

        user, created = User.objects.get_or_create(username=username)
        login(request, user)
        return redirect('dashboard')

    return HttpResponse("Login failed", status=401)

def dashboard(request):
    if request.user.is_authenticated:
        return render(request, 'dashboard.html')
    return redirect('login')

def logout_view(request):
    logout(request)
    return redirect('login')

