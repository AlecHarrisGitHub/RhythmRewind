from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from allauth.account.auth_backends import AuthenticationBackend
import os
from django.conf import settings
from urllib.parse import quote

import requests
import random
import json
from datetime import datetime
from collections import Counter

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_USER_PROFILE_URL = "https://api.spotify.com/v1/me"
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
SCOPE = "user-library-read user-top-read"

@login_required
def hangman_game(request):
    if request.user.is_authenticated:
        access_token = request.session.get('spotify_access_token')

        if not access_token:
            return redirect('spotify_login')

        # Fetch user's top tracks
        top_tracks_response = requests.get(
            "https://api.spotify.com/v1/me/top/tracks",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # Refresh token if necessary
        if top_tracks_response.status_code == 401:
            access_token = refresh_spotify_token(request.session)
            if access_token:
                top_tracks_response = requests.get(
                    "https://api.spotify.com/v1/me/top/tracks",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

        top_tracks_data = top_tracks_response.json()
        if top_tracks_response.status_code == 200 and 'items' in top_tracks_data:
            top_tracks = [track['name'] for track in top_tracks_data['items']]
        else:
            top_tracks = []

        # Select a random song as the phrase for the game
        phrase = random.choice(top_tracks) if top_tracks else "No Songs Found"

        return render(request, 'pages/hangman.html', {'phrase': phrase})

    return redirect('/account/login/')


def generate_text(request):
    response_text = "Error: Unable to generate text."
    if request.user.is_authenticated:
        access_token = request.session.get('spotify_access_token')

        if not access_token:
            return redirect('spotify_login')

        # Retrieve top tracks and track index from session
        top_tracks = request.session.get('top_tracks')
        track_index = request.session.get('track_index', 0)

        if not top_tracks:
            # Fetch top tracks if not in session
            top_tracks_response = requests.get(
                "https://api.spotify.com/v1/me/top/tracks?limit=50",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if top_tracks_response.status_code == 401:
                print("Access token expired, attempting to refresh.")
                access_token = refresh_spotify_token(request.session)
                if access_token:
                    top_tracks_response = requests.get(
                        "https://api.spotify.com/v1/me/top/tracks?limit=50",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )

            top_tracks_data = top_tracks_response.json()
            if top_tracks_response.status_code == 200 and 'items' in top_tracks_data:
                # Simplify data for session storage
                top_tracks = []
                for item in top_tracks_data['items']:
                    track_info = {
                        'name': item['name'],
                        'artist': item['artists'][0]['name']
                    }
                    top_tracks.append(track_info)
                request.session['top_tracks'] = top_tracks
                request.session['track_index'] = 0
                track_index = 0
            else:
                top_tracks = []
                request.session['top_tracks'] = []
                request.session['track_index'] = 0

        # Get the track at the current index
        if top_tracks and track_index < len(top_tracks):
            track = top_tracks[track_index]
            track_name = track['name']
            artist_name = track['artist']
            prompt = f"People who listen to {track_name} by {artist_name} tend to dress like"

            # Increment the track index for next time
            track_index += 1
            if track_index >= len(top_tracks):
                # Reset index to loop back to the first track
                track_index = 0
            request.session['track_index'] = track_index
        else:
            prompt = "People tend to dress"
            request.session['track_index'] = 0

        # Generate text using the prompt
        api_url = "https://api-inference.huggingface.co/models/gpt2"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
        payload = {"inputs": prompt, "parameters": {"max_length": 100}}

        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 200:
            response_text = response.json()[0]["generated_text"]
        else:
            response_text = "Error: Unable to generate text."

        # Handle AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'response_text': response_text})

        return render(request, 'pages/ai_result.html', {'response': response_text})

    else:
        return redirect('login')




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
            "https://api.spotify.com/v1/me/top/tracks?limit=50",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        top_artists_response = requests.get(
            "https://api.spotify.com/v1/me/top/artists?limit=50",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # Refresh token if expired
        if top_tracks_response.status_code == 401:
            access_token = refresh_spotify_token(request.session)
            if access_token:
                top_tracks_response = requests.get(
                    "https://api.spotify.com/v1/me/top/tracks?limit=50",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                top_artists_response = requests.get(
                    "https://api.spotify.com/v1/me/top/artists?limit=50",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

        # Parse data
        track_names, popularity_scores = [], []
        artist_names, artist_followers = [], []
        listening_time_data = [0] * 7  # Initialize list for 7 days of the week
        genre_list = []
        release_years = []
        valence_list = []
        energy_list = []
        scatter_track_names = []

        if top_tracks_response.status_code == 200:
            top_tracks_data = top_tracks_response.json().get('items', [])
            track_ids = []
            for track in top_tracks_data:
                track_names.append(track['name'])
                popularity_scores.append(track['popularity'])
                track_ids.append(track['id'])
                # Get release date of the track's album
                album_release_date = track['album']['release_date']
                if album_release_date:
                    release_year = int(album_release_date.split('-')[0])
                    release_years.append(release_year)

            # Fetch audio features for top tracks
            if track_ids:
                ids_param = ','.join(track_ids)
                audio_features_response = requests.get(
                    "https://api.spotify.com/v1/audio-features",
                    params={'ids': ids_param},
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if audio_features_response.status_code == 200:
                    audio_features_data = audio_features_response.json().get('audio_features', [])
                    for i, af in enumerate(audio_features_data):
                        if af:
                            valence_list.append(af.get('valence', 0))
                            energy_list.append(af.get('energy', 0))
                            scatter_track_names.append(track_names[i])

        # Prepare data for the Valence vs. Energy Scatter Plot
        scatter_data = []
        for i in range(len(scatter_track_names)):
            scatter_data.append({
                'x': valence_list[i],
                'y': energy_list[i],
                'label': scatter_track_names[i]
            })

        # Prepare data for release years chart
        year_counts = Counter(release_years)
        years = sorted(year_counts.keys())
        year_frequencies = [year_counts[year] for year in years]

        if top_artists_response.status_code == 200:
            top_artists_data = top_artists_response.json().get('items', [])
            for artist in top_artists_data:
                artist_names.append(artist['name'])
                artist_followers.append(artist['followers']['total'])
                genre_list.extend(artist['genres'])

        # Prepare data for genres chart
        genre_counts = Counter(genre_list)
        most_common_genres = genre_counts.most_common(5)
        genre_labels = [genre for genre, count in most_common_genres]
        genre_values = [count for genre, count in most_common_genres]

        # Round the listening_time_data without json.dumps
        listening_time_data = [round(hour, 2) for hour in listening_time_data]

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
            'track_names': json.dumps(track_names),
            'popularity_scores': json.dumps(popularity_scores),
            'artist_names': json.dumps(artist_names),
            'artist_followers': json.dumps(artist_followers),
            'listening_time_data': listening_time_data,  # Pass as a list
            'genre_labels': json.dumps(genre_labels),
            'genre_values': json.dumps(genre_values),
            'scatter_data': json.dumps(scatter_data),
            'years': json.dumps(years),
            'year_frequencies': json.dumps(year_frequencies),
            'user_profile': user_profile
        })

    return redirect('/account/login/')

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

def home(request):
    return render(request, 'pages/home.html')


