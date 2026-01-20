"""
Playlist generation algorithm for Marathon Music.
Selects and orders songs based on race pacing and energy requirements.
"""


def calculate_target_cadence(distance_km, goal_time_min):
    """
    Calculate target running cadence based on pace.

    Args:
        distance_km: Race distance in kilometers
        goal_time_min: Goal finish time in minutes

    Returns:
        Target cadence in steps per minute (typically 170-180)
    """
    # Calculate pace in min/km
    pace_min_per_km = goal_time_min / distance_km

    # Faster pace = higher cadence (rough approximation)
    # Elite runners: ~3:00/km pace → 180 spm
    # Recreational: ~6:00/km pace → 170 spm
    if pace_min_per_km < 4.0:
        return 180
    elif pace_min_per_km < 5.0:
        return 175
    else:
        return 170


def define_race_phases(distance_km, goal_time_min):
    """
    Define race phases with time ranges and energy targets.

    Args:
        distance_km: Race distance in kilometers
        goal_time_min: Goal finish time in minutes

    Returns:
        List of phase dictionaries with name, start_time, end_time, energy_range
    """
    phases = [
        {
            'name': 'Warmup',
            'start_pct': 0.0,
            'end_pct': 0.05,
            'energy_min': 0.5,
            'energy_max': 0.6
        },
        {
            'name': 'Settle',
            'start_pct': 0.05,
            'end_pct': 0.30,
            'energy_min': 0.5,
            'energy_max': 0.65
        },
        {
            'name': 'Cruise',
            'start_pct': 0.30,
            'end_pct': 0.55,
            'energy_min': 0.6,
            'energy_max': 0.7
        },
        {
            'name': 'Grind',
            'start_pct': 0.55,
            'end_pct': 0.75,
            'energy_min': 0.7,
            'energy_max': 0.8
        },
        {
            'name': 'Wall',
            'start_pct': 0.75,
            'end_pct': 0.90,
            'energy_min': 0.80,
            'energy_max': 1.0
        },
        {
            'name': 'Glory',
            'start_pct': 0.90,
            'end_pct': 1.0,
            'energy_min': 0.85,
            'energy_max': 1.0
        }
    ]

    # Convert percentages to actual times in minutes
    for phase in phases:
        phase['start_time'] = phase['start_pct'] * goal_time_min
        phase['end_time'] = phase['end_pct'] * goal_time_min
        phase['duration'] = phase['end_time'] - phase['start_time']

    return phases


def filter_tracks_for_phase(tracks, phase, target_cadence, bpm_tolerance=5):
    """
    Filter tracks suitable for a specific race phase.

    Args:
        tracks: List of track dictionaries with audio features
        phase: Phase dictionary with energy requirements
        target_cadence: Target BPM (or half-BPM is also acceptable)
        bpm_tolerance: How much BPM can deviate from target

    Returns:
        List of suitable tracks for this phase
    """
    suitable_tracks = []

    for track in tracks:
        tempo = track['tempo']
        energy = track['energy']

        # Check if BPM matches target cadence or half-cadence
        # e.g., if target is 175, accept 170-180 or 85-90
        matches_full_cadence = (target_cadence - bpm_tolerance <= tempo <= target_cadence + bpm_tolerance)
        matches_half_cadence = (target_cadence/2 - bpm_tolerance <= tempo <= target_cadence/2 + bpm_tolerance)
        matches_double_cadence = (target_cadence*2 - bpm_tolerance <= tempo <= target_cadence*2 + bpm_tolerance)

        # Check if energy level matches phase requirements
        matches_energy = (phase['energy_min'] <= energy <= phase['energy_max'])

        if (matches_full_cadence or matches_half_cadence or matches_double_cadence) and matches_energy:
            suitable_tracks.append(track)

    return suitable_tracks


def fill_phase_duration(tracks, phase_duration_min):
    """
    Select tracks to fill the phase duration without going over too much.

    Args:
        tracks: List of suitable tracks for this phase
        phase_duration_min: How long this phase should be (in minutes)

    Returns:
        List of selected tracks
    """
    if not tracks:
        return []

    target_duration_ms = phase_duration_min * 60 * 1000
    selected_tracks = []
    current_duration_ms = 0

    # Sort by energy for gradual build (or use valence, danceability as tiebreakers)
    # For simplicity, we'll just randomly sample and try to fill duration
    available_tracks = tracks.copy()

    while current_duration_ms < target_duration_ms and available_tracks:
        # Pick the next track
        # Simple approach: just take tracks in order
        # More sophisticated: sort by energy, valence, etc.
        track = available_tracks.pop(0)
        selected_tracks.append(track)
        current_duration_ms += track['duration_ms']

    return selected_tracks


def generate_playlist(tracks, distance_km, goal_time_min):
    """
    Main algorithm: generate a race-optimized playlist.

    Args:
        tracks: List of track dictionaries with audio features
        distance_km: Race distance in kilometers
        goal_time_min: Goal finish time in minutes

    Returns:
        Ordered list of tracks for the playlist
    """
    print(f"\nGenerating playlist for {distance_km}km in {goal_time_min} minutes...")

    # Step 1: Calculate target cadence
    target_cadence = calculate_target_cadence(distance_km, goal_time_min)
    print(f"Target cadence: {target_cadence} spm")

    # Step 2: Define race phases
    phases = define_race_phases(distance_km, goal_time_min)

    # Step 3: Build playlist phase by phase
    playlist = []
    bpm_tolerance = 5

    for phase in phases:
        print(f"\nPhase: {phase['name']} ({phase['duration']:.1f} min, energy {phase['energy_min']}-{phase['energy_max']})")

        # Filter tracks for this phase
        suitable_tracks = filter_tracks_for_phase(
            tracks,
            phase,
            target_cadence,
            bpm_tolerance
        )

        print(f"  Found {len(suitable_tracks)} suitable tracks")

        # If not enough tracks, relax BPM constraint
        if len(suitable_tracks) < 3:
            print(f"  Not enough tracks, relaxing BPM tolerance to 10")
            suitable_tracks = filter_tracks_for_phase(
                tracks,
                phase,
                target_cadence,
                bpm_tolerance=10
            )

        # If still not enough, just use any tracks with matching energy
        if len(suitable_tracks) < 3:
            print(f"  Still not enough, using any tracks with matching energy")
            suitable_tracks = [
                t for t in tracks
                if phase['energy_min'] <= t['energy'] <= phase['energy_max']
            ]

        # Fill this phase
        phase_tracks = fill_phase_duration(suitable_tracks, phase['duration'])
        print(f"  Selected {len(phase_tracks)} tracks")

        playlist.extend(phase_tracks)

    print(f"\nTotal playlist: {len(playlist)} tracks, {sum(t['duration_ms'] for t in playlist) / 60000:.1f} minutes")

    return playlist
