from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from allauth.account.auth_backends import AuthenticationBackend
import os
from django.conf import settings
from urllib.parse import quote
import requests
import random
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify


SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_USER_PROFILE_URL = "https://api.spotify.com/v1/me"
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
SCOPE = "user-library-read user-top-read"


def generate_text(request):
    response_text = "Error: Unable to generate text."
    if request.user.is_authenticated:
        access_token = request.session.get('spotify_access_token')

        if not access_token:
            return redirect('spotify_login')

        # Fetch top tracks
        top_tracks_response = requests.get(
            "https://api.spotify.com/v1/me/top/tracks",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if top_tracks_response.status_code == 401:
            print("Access token expired, attempting to refresh.")
            access_token = refresh_spotify_token(request.session)
            if access_token:
                top_tracks_response = requests.get(
                    "https://api.spotify.com/v1/me/top/tracks",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

        top_tracks_data = top_tracks_response.json()
        prompt = "People tend to dress"
        if top_tracks_response.status_code == 200 and 'items' in top_tracks_data:
            top_tracks = top_tracks_data['items']
            if top_tracks:
                first_track = top_tracks[0]
                track_name = first_track['name']
                artist_name = first_track['artists'][0]['name']
                prompt = f"People who listen to {track_name} by {artist_name} tend to dress like"

        api_url = "https://api-inference.huggingface.co/models/gpt2"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
        payload = {"inputs": prompt, "parameters": {"max_length": 100}}

        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 200:
            response_text = response.json()[0]["generated_text"]
        else:
            response_text = "Error: Unable to generate text."

    return render(request, 'pages/ai_result.html', {'response': response_text})


def spotify_login(request):
    auth_url = (
        f"{SPOTIFY_AUTH_URL}?client_id={CLIENT_ID}&response_type=code"
        f"&redirect_uri={REDIRECT_URI}&scope={quote(SCOPE)}&show_dialog=true"
    )
    return redirect(auth_url)

@login_required
def spotify_game(request):
    # Retrieve the user's Spotify access token
    access_token = request.session.get('spotify_access_token')

    if not access_token:
        return redirect('spotify_login')

    # Fetch the user's top tracks to ensure we provide a song they haven't heard before
    top_tracks_response = requests.get(
        "https://api.spotify.com/v1/me/top/tracks",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    # Parse the user's top tracks to get their names
    top_track_names = []
    if top_tracks_response.status_code == 200:
        top_tracks_data = top_tracks_response.json().get('items', [])
        for track in top_tracks_data:
            top_track_names.append(track['name'])

    # Fetch new music recommendations
    recommendations_response = requests.get(
        "https://api.spotify.com/v1/recommendations",
        params={"seed_genres": "pop,rock", "limit": 10},
        headers={"Authorization": f"Bearer {access_token}"}
    )

    new_song = None
    clue = None
    popularity_label = "lesser-known"
    if recommendations_response.status_code == 200:
        recommendations_data = recommendations_response.json().get('tracks', [])
        for track in recommendations_data:
            if track['name'] not in top_track_names:
                new_song = track
                break

    # If a new song was found, create a game clue
    if new_song:
        artist_name = new_song['artists'][0]['name']
        popularity = new_song.get('popularity', 0)
        popularity_label = "popular" if popularity > 70 else "lesser-known"

        clue = (
            f"Guess the artist: Their name starts with '{artist_name[0]}' "
            f"and they are known for the song '{new_song['name'][0]}...'."
        )

    return render(request, 'pages/spotify_game.html', {
        'clue': clue,
        'new_song': {
            'name': new_song['name'],
            'artists': [artist['name'] for artist in new_song['artists']],
            'external_url': new_song['external_urls']['spotify'],
            'popularity_label': popularity_label
        }
    })



@login_required
def dashboard(request):
    if request.user.is_authenticated:
        access_token = request.session.get('spotify_access_token')

        if not access_token:
            return redirect('spotify_login')

        # Fetch Spotify data
        top_tracks_response = requests.get(
            "https://api.spotify.com/v1/me/top/tracks",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        top_artists_response = requests.get(
            "https://api.spotify.com/v1/me/top/artists",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        recently_played_response = requests.get(
            "https://api.spotify.com/v1/me/player/recently-played",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # Refresh token if expired
        if top_tracks_response.status_code == 401:
            access_token = refresh_spotify_token(request.session)
            if access_token:
                top_tracks_response = requests.get(
                    "https://api.spotify.com/v1/me/top/tracks",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                top_artists_response = requests.get(
                    "https://api.spotify.com/v1/me/top/artists",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                recently_played_response = requests.get(
                    "https://api.spotify.com/v1/me/player/recently-played",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

        # Parse data
        top_tracks, track_names, popularity_scores = [], [], []
        top_artists, artist_names, artist_followers = [], [], []
        recently_played_names, play_counts = [], []

        if top_tracks_response.status_code == 200:
            top_tracks_data = top_tracks_response.json().get('items', [])
            for track in top_tracks_data:
                track_names.append(track['name'])
                popularity_scores.append(track['popularity'])

        if top_artists_response.status_code == 200:
            top_artists_data = top_artists_response.json().get('items', [])
            for artist in top_artists_data:
                artist_names.append(artist['name'])
                artist_followers.append(artist['followers']['total'])

        if recently_played_response.status_code == 200:
            recently_played_data = recently_played_response.json().get('items', [])
            track_count = {}
            for item in recently_played_data:
                track_name = item['track']['name']
                track_count[track_name] = track_count.get(track_name, 0) + 1

            recently_played_names = list(track_count.keys())
            play_counts = list(track_count.values())

        profile_response = requests.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_profile = {}
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            user_profile = {
                'display_name': profile_data.get('display_name'),
                'profile_image': profile_data['images'][0]['url'] if profile_data.get('images') else None,
                'followers': profile_data.get('followers', {}).get('total', 0)
            }

        return render(request, 'pages/dashboard.html', {
            'track_names': track_names,
            'popularity_scores': popularity_scores,
            'artist_names': artist_names,
            'artist_followers': artist_followers,
            'recently_played_names': recently_played_names,
            'play_counts': play_counts,
            'user_profile': user_profile
        })

    return redirect('/accounts/login/')


def spotify_callback(request):
    code = request.GET.get('code')
    if not code:
        return HttpResponse("Login failed", status=401)

    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_info = response.json()

    if "access_token" in token_info:
        access_token = token_info['access_token']
        refresh_token = token_info.get('refresh_token')

        request.session['spotify_access_token'] = access_token
        if refresh_token:
            request.session['spotify_refresh_token'] = refresh_token

        profile_response = requests.get(
            SPOTIFY_USER_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if profile_response.status_code != 200:
            return HttpResponse(
                f"Error: {profile_response.status_code} - {profile_response.text}",
                status=profile_response.status_code
            )

        try:
            profile_data = profile_response.json()
        except ValueError as e:
            return HttpResponse(
                f"JSON Decode Error: {str(e)}. Response Content: {profile_response.text}",
                status=500
            )

        if 'id' in profile_data:
            username = profile_data['id']
            user, created = User.objects.get_or_create(username=username)
            login(request, user, backend='allauth.account.auth_backends.AuthenticationBackend')
            return redirect('dashboard')

    return HttpResponse("Login failed", status=401)


def refresh_spotify_token(session):
    refresh_token = session.get('spotify_refresh_token')
    if not refresh_token:
        return None

    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_info = response.json()
    new_access_token = token_info.get('access_token')

    if new_access_token:
        session['spotify_access_token'] = new_access_token
        return new_access_token
    return None


@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        user.delete()
        messages.success(request, "Your account has been deleted successfully.")
        return redirect('login')
    return render(request, 'pages/delete_account.html')


def logout_view(request):
    logout(request)
    return redirect('login')

def contact(request):
    staff_members = [
        {"name": "Staff Member 1", "position": "Manager", "email": "staff1@example.com"},
        {"name": "Staff Member 2", "position": "Developer", "email": "staff2@example.com"},
        {"name": "Staff Member 3", "position": "Designer", "email": "staff3@example.com"},
        {"name": "Staff Member 4", "position": "Marketer", "email": "staff4@example.com"},
        {"name": "Staff Member 5", "position": "Support", "email": "staff5@example.com"},
    ]
    return render(request, 'pages/contact.html', {"staff_members": staff_members})

sp = Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-top-read"
    ))
top_artists_response = sp.current_user_top_artists(limit=1)
top_artist = top_artists_response['items'][0] if top_artists_response['items'] else None

# def wraps(request):
#     summaries = [
#         {"title": " ",
#             "description": " ",
#             "image_url": "https://via.placeholder.com/800x300/ff80bf/000000?text=Continue to get your rewind!",},
#         {"title": "filler", "description": " ", "image_url": "https://via.placeholder.com/800x300/ff80bf/000000?text=Putting the 'art' in artist!",},
#         {"title": f"Top Artist: {top_artist['name']}" if top_artist else "Top Artist: Unknown",
#             "description": f"Genre: {', '.join(top_artist['genres'])}" if top_artist else "No artist data found.",
#             "image_url": top_artist['images'][0]['url'] if top_artist and top_artist['images'] else "https://via.placeholder.com/800x300?text=No+Image",},
#
#         {"title": "filler", "description": " ", "image_url": "https://via.placeholder.com/800x300/ff80bf/000000?text=This next song has been your anthem!",},
#         {"title": "Top Song", "description": " ", "image_url": "https://via.placeholder.com/800x300?text=Summary+4"},
#         {"title": "filler", "description": " ", "image_url": "https://via.placeholder.com/800x300/ff80bf/000000?text=Let's take a look at your follows...",},
#         {"title": "Number of Followers", "description": "followers", "image_url": "https://via.placeholder.com/800x300?text=Summary+6"},
#         {"title": "filler", "description": "Let's take a look at a summary of your rad tunes!", "image_url": "https://via.placeholder.com/800x300/ff80bf/000000?text=Here's a summary of all your rad tunes!",},
#         {"title": "Summary", "description": "This is the eighth summary of your wrap!", "image_url": "https://via.placeholder.com/800x300?text=Summary+8"},
#     ]
#     return render(request, 'pages/wraps.html', {"summaries": summaries})
@login_required
def wraps(request):
    access_token = request.session.get('spotify_access_token')

    if not access_token:
        return redirect('spotify_login')

    # Fetch user's top artist
    top_artists_response = requests.get(
        "https://api.spotify.com/v1/me/top/artists",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if top_artists_response.status_code == 401:
        access_token = refresh_spotify_token(request.session)
        if access_token:
            top_artists_response = requests.get(
                "https://api.spotify.com/v1/me/top/artists",
                headers={"Authorization": f"Bearer {access_token}"}
            )

    top_artist = None
    if top_artists_response.status_code == 200:
        top_artists_data = top_artists_response.json().get('items', [])
        if top_artists_data:
            top_artist = top_artists_data[0]

    # Prepare summaries for carousel slides
    summaries = [
        {
            "title": "Welcome to Your Latest Rhythm Rewind!",
            "description": "Continue to get your rewind!",
            "image_url": "https://via.placeholder.com/800x300/ff80bf/000000?text=Continue+to+get+your+rewind!",
        },
        {
            "title": f"Top Artist: {top_artist['name']}" if top_artist else "Top Artist: Unknown",
            "description": f"Genre: {', '.join(top_artist['genres'])}" if top_artist else "No artist data found.",
            "image_url": top_artist['images'][0]['url'] if top_artist and top_artist['images'] else "https://via.placeholder.com/800x300?text=No+Image",
        },
        {
            "title": "Now take a look at your top song",
            "description": "",
            "image_url": "https://via.placeholder.com/800x300/ff80bf/000000?text=This+next+song+has+been+your+anthem!",
        },
        # Add additional slides as needed...
    ]

    return render(request, 'pages/wraps.html', {"summaries": summaries})
