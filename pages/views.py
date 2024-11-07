from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import requests
import os
from django.conf import settings

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_USER_PROFILE_URL = "https://api.spotify.com/v1/me"
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
SCOPE = "user-read-playback-state user-library-read"



def generate_text(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt')

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

    return render(request, 'pages/ai_input.html')

def spotify_login(request):
    auth_url = (
        f"{SPOTIFY_AUTH_URL}?client_id={CLIENT_ID}&response_type=code"
        f"&redirect_uri={REDIRECT_URI}&scope={SCOPE}"
    )
    return redirect(auth_url)

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

        # Fetch user profile data
        profile_response = requests.get(
            SPOTIFY_USER_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        profile_data = profile_response.json()

        if 'id' in profile_data:
            username = profile_data['id']
            user, created = User.objects.get_or_create(username=username)
            login(request, user)
            return redirect('dashboard')

    return HttpResponse("Login failed", status=401)

@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        user.delete()
        messages.success(request, "Your account has been deleted successfully.")
        return redirect('login')
    return render(request, 'pages/delete_account.html')

def dashboard(request):
    if request.user.is_authenticated:
        return render(request, 'dashboard.html')
    return redirect('login')

def logout_view(request):
    logout(request)
    return redirect('login')
