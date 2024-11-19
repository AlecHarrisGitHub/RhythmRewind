from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from allauth.account.auth_backends import AuthenticationBackend
import requests
import os
from django.conf import settings
from urllib.parse import quote
import random

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

    return redirect('/accounts/login/')

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

        # If access is unauthorized, attempt to refresh the token
        if top_tracks_response.status_code == 401:
            print("Access token expired, attempting to refresh.")
            access_token = refresh_spotify_token(request.session)
            if access_token:
                # Retry fetching top tracks with the new access token
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
                prompt = "People who listen to " + track_name + " by " + artist_name + " tend to dress like"
        # Hugging Face API setup
        api_url = "https://api-inference.huggingface.co/models/gpt2"  # Replace with your preferred model
        headers = {
            "Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"
        }
        payload = {
            "inputs": prompt,
            "parameters": {"max_length": 100}  # Adjust as needed
        }

        # Send request to Hugging Face API
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
def dashboard(request):
    if request.user.is_authenticated:
        access_token = request.session.get('spotify_access_token')

        if not access_token:
            return redirect('spotify_login')

        # Attempt to fetch top tracks
        top_tracks_response = requests.get(
            "https://api.spotify.com/v1/me/top/tracks",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # If access is unauthorized, attempt to refresh the token
        if top_tracks_response.status_code == 401:
            print("Access token expired, attempting to refresh.")
            access_token = refresh_spotify_token(request.session)
            if access_token:
                # Retry fetching top tracks with the new access token
                top_tracks_response = requests.get(
                    "https://api.spotify.com/v1/me/top/tracks",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

        top_tracks_data = top_tracks_response.json()
        if top_tracks_response.status_code == 200 and 'items' in top_tracks_data:
            top_tracks = top_tracks_data['items']
            # Print the first song's name and artist's name if available
            if top_tracks:
                first_track = top_tracks[0]
                track_name = first_track['name']
                artist_name = first_track['artists'][0]['name']
        else:
            top_tracks = []

        return render(request, 'pages/dashboard.html', {'top_tracks': top_tracks})

    return redirect('/accounts/login/')


def spotify_callback(request):
    code = request.GET.get('code')
    if not code:
        return HttpResponse("Login failed", status=401)

    # Requesting access token
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
        refresh_token = token_info.get('refresh_token')  # Spotify returns this only on initial login

        # Store tokens in the session
        request.session['spotify_access_token'] = access_token
        if refresh_token:
            request.session['spotify_refresh_token'] = refresh_token

        # Fetch user profile data
        profile_response = requests.get(
            SPOTIFY_USER_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        profile_data = profile_response.json()

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

    # Update session with the new access token
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
