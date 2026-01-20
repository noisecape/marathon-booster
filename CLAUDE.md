# Marathon Music - Project Brief

## What We're Building

A Flask web app that generates personalized Spotify playlists optimized for marathon (or any distance) running performance. The user inputs their goal time, and the app creates a playlist that follows the pacing and energy arc of the race.

This is a **Level 1 POC** — no real-time adaptation yet. We're testing the hypothesis that intelligently sequenced music (correct BPM for cadence, energy curve matching race phases) improves running performance.

## Core Concept

Music can improve endurance performance through:
- **Cadence synchronization**: BPM matching footstrike rate (~170-180 steps/min)
- **Arousal regulation**: Energy levels matching race phase demands
- **Distraction**: High-valence music during hard efforts

## User Flow

1. User visits the app
2. "Login with Spotify" → OAuth flow
3. User inputs: race distance + goal time
4. App fetches user's saved songs from Spotify
5. App fetches audio features (BPM, energy, valence) for those songs
6. Algorithm builds playlist following race arc
7. Playlist is created in user's Spotify account
8. User opens Spotify and runs with it

## Architecture

```
Browser (Frontend) ←→ Flask Server ←→ Spotify API
                          │
                          ▼
                   Playlist Algorithm
```

- **Frontend**: Simple HTML form (goal time, distance, submit button)
- **Backend**: Flask handles OAuth, API calls, algorithm orchestration
- **Spotify API**: Auth, fetch songs, fetch audio features, create playlist
- **Algorithm**: Rule-based song selection and ordering

## Spotify Audio Features We Use

| Feature | Range | Purpose |
|---------|-------|---------|
| `tempo` | BPM | Match to running cadence |
| `energy` | 0-1 | Intensity, maps to race phases |
| `valence` | 0-1 | Positivity, for motivation |
| `danceability` | 0-1 | Rhythm consistency |

## The Algorithm Logic

### Step 1: Calculate target cadence
- Derive target pace from goal time + distance
- Map to cadence (typically 170-180 spm)
- Allow songs at cadence BPM or half-cadence (e.g., 175 or 87-88 BPM)

### Step 2: Define race phases
For a marathon:
| Phase | % of race | Energy target | Purpose |
|-------|-----------|---------------|---------|
| Warmup | 0-5% | 0.5-0.6 | Controlled start |
| Settle | 5-30% | 0.5-0.65 | Find rhythm |
| Cruise | 30-55% | 0.6-0.7 | Steady state |
| Grind | 55-75% | 0.7-0.8 | Building effort |
| Wall | 75-90% | 0.85+ | Survive and push |
| Glory | 90-100% | 0.9+ | Everything left |

### Step 3: Select and order songs
- Filter by BPM range (target cadence ± 5)
- Filter by energy range for each phase
- Fill each phase to its duration
- Handle edge cases (not enough songs → relax filters)

## Project Structure

```
marathon-music/
├── CLAUDE.md           # This file - project context
├── README.md           # Public-facing docs
├── .env                # Spotify credentials (DO NOT COMMIT)
├── .gitignore
├── requirements.txt
├── app.py              # Flask routes, OAuth, API calls
├── algorithm.py        # Playlist generation logic
└── templates/
    └── index.html      # Simple form UI
```

## Spotify API Setup Required

1. Go to https://developer.spotify.com/dashboard
2. Create an app
3. Get Client ID and Client Secret
4. Add redirect URI: `http://localhost:5000/callback`
5. Store credentials in `.env`:
   ```
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   SPOTIFY_REDIRECT_URI=http://localhost:5000/callback
   ```

## Key Dependencies

- `flask` - Web server
- `spotipy` - Spotify API wrapper (handles OAuth nicely)
- `python-dotenv` - Load .env file

## Current Status

Project scaffolding phase. Need to:
1. [x] Define architecture and algorithm
2. [ ] Set up Flask with Spotify OAuth
3. [ ] Implement song fetching + audio features
4. [ ] Implement playlist algorithm
5. [ ] Implement playlist creation
6. [ ] Build simple frontend form
7. [ ] Test end-to-end

## Future Enhancements (Not for POC)

- **Level 2**: Real-time adaptation using phone GPS + Bluetooth HR strap
- **ML personalization**: Use historical Strava data to learn which songs correlate with performance improvements for this specific runner
- **Integrated playback**: Spotify SDK for in-app playback control

## Notes for Claude

- The user is an AI research engineer, comfortable with Python but less familiar with web dev patterns (Flask, OAuth, APIs)
- Explain web concepts when they come up
- Keep the POC simple — we're validating the concept, not building a production app
- User has Garmin watch + chest strap HR monitor, and historical run data in Strava (for future use)
