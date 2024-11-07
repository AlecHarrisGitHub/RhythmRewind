from django.shortcuts import redirect, render
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.http import HttpResponse, JsonResponse
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
import random


# Spotify Login View
def spotify_login(request):
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv('SPOTIFY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
        scope="user-read-playback-state user-library-read user-top-read"
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


# Spotify Callback View
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

        # Save tokens in session
        request.session['spotify_access_token'] = token_info['access_token']
        return redirect('dashboard')

    return HttpResponse("Login failed", status=401)


# Dashboard View
def dashboard(request):
    if request.user.is_authenticated:
        return render(request, 'dashboard.html')
    return redirect('login')


# Logout View
def logout_view(request):
    logout(request)
    return redirect('login')


# Summary Page View
def summary_page(request):
    if not request.user.is_authenticated:
        return redirect('login')

    access_token = request.session.get('spotify_access_token')
    if not access_token:
        return redirect('spotify_login')

    sp = Spotify(auth=access_token)
    top_tracks = sp.current_user_top_tracks(limit=10)

    # Prepare the top tracks data for rendering
    track_data = [
        {
            'name': track['name'],
            'artists': [artist['name'] for artist in track['artists']],
            'album_image_url': track['album']['images'][0]['url'] if track['album']['images'] else ''
        }
        for track in top_tracks['items']
    ]

    return render(request, 'summary.html', {'top_tracks': track_data})


# Spin-the-Wheel Game View
def spin_wheel(request):
    if not request.user.is_authenticated:
        return redirect('login')

    access_token = request.session.get('spotify_access_token')
    if not access_token:
        return redirect('spotify_login')

    sp = Spotify(auth=access_token)
    recommendations = sp.recommendations(seed_tracks=None, limit=10)  # Modify with your logic
    random_song = random.choice(recommendations['tracks'])

    song_data = {
        'name': random_song['name'],
        'artists': [artist['name'] for artist in random_song['artists']],
        'preview_url': random_song.get('preview_url', ''),
        'album_image_url': random_song['album']['images'][0]['url'] if random_song['album']['images'] else ''
    }

    return JsonResponse(song_data)
