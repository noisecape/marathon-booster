"""
Flask app for Marathon Music - Spotify playlist generator for runners.
Handles OAuth, Spotify API calls, and playlist creation.
"""

import os
from flask import Flask, render_template, request, redirect, session, url_for
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from algorithm import generate_playlist

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Spotify API configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')

# Scopes needed: read user's saved tracks, create playlists, get audio features
SCOPE = 'user-library-read playlist-modify-public playlist-modify-private'


def get_spotify_oauth():
    """Create a SpotifyOAuth object for handling authentication."""
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE,
        cache_path=None,  # Don't cache to disk, use session instead
        show_dialog=True
    )


@app.route('/')
def index():
    """Landing page with login option."""
    return render_template('index.html')


@app.route('/login')
def login():
    """Redirect user to Spotify's authorization page."""
    sp_oauth = get_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """
    Spotify redirects here after user authorizes.
    Exchange the authorization code for an access token.
    """
    sp_oauth = get_spotify_oauth()

    # Clear any old session data
    session.clear()

    # Get the authorization code from the URL
    code = request.args.get('code')

    # Exchange code for access token
    token_info = sp_oauth.get_access_token(code)

    # Store token in session
    session['token_info'] = token_info

    return redirect(url_for('create_playlist_form'))


@app.route('/create-playlist')
def create_playlist_form():
    """Form where user inputs race distance and goal time."""
    # Check if user is authenticated
    if 'token_info' not in session:
        return redirect(url_for('login'))

    return render_template('create_playlist.html')


@app.route('/generate', methods=['POST'])
def generate():
    """
    Generate the playlist based on user inputs.
    1. Fetch user's saved songs
    2. Get audio features for those songs
    3. Run algorithm to create playlist
    4. Create playlist in user's Spotify account
    """
    # Check if user is authenticated
    if 'token_info' not in session:
        return redirect(url_for('login'))

    # Get form data
    distance = float(request.form.get('distance'))  # in kilometers
    goal_time = int(request.form.get('goal_time'))  # in minutes

    # Create Spotify client
    sp = spotipy.Spotify(auth=session['token_info']['access_token'])

    try:
        # Step 1: Fetch user's saved tracks
        print("Fetching user's saved tracks...")
        saved_tracks = []
        results = sp.current_user_saved_tracks(limit=50)

        while results:
            saved_tracks.extend(results['items'])
            if results['next']:
                results = sp.next(results)
            else:
                break

        print(f"Found {len(saved_tracks)} saved tracks")

        # Step 2: Extract track IDs and get audio features
        print("Fetching audio features...")
        track_ids = [item['track']['id'] for item in saved_tracks if item['track']['id']]

        # Spotify API limits: 100 tracks per request
        all_features = []
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i+100]
            features = sp.audio_features(batch)
            all_features.extend([f for f in features if f is not None])

        # Combine track info with audio features
        tracks_with_features = []
        for item, features in zip(saved_tracks, all_features):
            if features:
                tracks_with_features.append({
                    'id': item['track']['id'],
                    'name': item['track']['name'],
                    'artist': item['track']['artists'][0]['name'],
                    'duration_ms': item['track']['duration_ms'],
                    'tempo': features['tempo'],
                    'energy': features['energy'],
                    'valence': features['valence'],
                    'danceability': features['danceability']
                })

        print(f"Got audio features for {len(tracks_with_features)} tracks")

        # Step 3: Generate playlist using algorithm
        print("Generating playlist...")
        playlist_tracks = generate_playlist(
            tracks_with_features,
            distance,
            goal_time
        )

        if not playlist_tracks:
            return "Not enough suitable tracks found! Try saving more songs to your Spotify library.", 400

        # Step 4: Create playlist in user's account
        print("Creating Spotify playlist...")
        user_id = sp.current_user()['id']

        playlist_name = f"Marathon Music - {distance}km in {goal_time}min"
        playlist_description = f"Auto-generated running playlist for {distance}km at {goal_time/60:.1f}h pace. BPM-optimized for your cadence."

        playlist = sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=False,
            description=playlist_description
        )

        # Add tracks to playlist (max 100 at a time)
        track_uris = [f"spotify:track:{track['id']}" for track in playlist_tracks]
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            sp.playlist_add_items(playlist['id'], batch)

        print(f"Playlist created: {playlist['external_urls']['spotify']}")

        return render_template(
            'success.html',
            playlist_url=playlist['external_urls']['spotify'],
            playlist_name=playlist_name,
            num_tracks=len(playlist_tracks),
            duration_min=sum(t['duration_ms'] for t in playlist_tracks) // 60000
        )

    except Exception as e:
        print(f"Error: {e}")
        return f"An error occurred: {str(e)}", 500


if __name__ == '__main__':
    # Check that environment variables are set
    if not all([SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI]):
        print("ERROR: Missing Spotify API credentials!")
        print("Please set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI in .env file")
        exit(1)

    app.run(debug=True, port=5000)
