import librosa
import numpy as np
from logger import get_logger
from pydub import AudioSegment

logger = get_logger(__name__)

MUSIC_DIR = "music"


def align_beats(y1, sample_rate1, y2, sample_rate2):
    """Align the beats of two audio tracks."""
    # Get beat times for both tracks
    # Process audio in smaller chunks to reduce memory usage
    _, beats1 = librosa.beat.beat_track(y=y1[: len(y1) // 2], sr=sample_rate1)
    _, beats2 = librosa.beat.beat_track(y=y2[: len(y2) // 2], sr=sample_rate2)

    # Convert beat frames to times
    beat_times1 = librosa.frames_to_time(frames=beats1, sr=sample_rate1)
    beat_times2 = librosa.frames_to_time(frames=beats2, sr=sample_rate2)

    # Find the first prominent beat in each track
    first_beat1 = beat_times1[0] if len(beat_times1) > 0 else 0
    first_beat2 = beat_times2[0] if len(beat_times2) > 0 else 0

    # Calculate time shift to align the beats
    time_shift = first_beat2 - first_beat1

    # Apply time shift (pad with silence or trim the start)
    if time_shift > 0:
        y1_aligned = librosa.util.fix_length(
            data=y1, size=len(y1) + int(sample_rate1 * time_shift)
        )
        y2_aligned = y2
    else:
        y1_aligned = y1
        y2_aligned = librosa.util.fix_length(
            data=y2, size=len(y2) - int(sample_rate2 * time_shift)
        )

    return y1_aligned, y2_aligned


def numpy_to_audiosegment(y, sr):
    """Convert a numpy array to a PyDub AudioSegment in highest quality."""
    # Convert to 32-bit float PCM
    y = (y * 2147483647).astype(np.int32)  # Scale to 32-bit range
    # Create AudioSegment
    audio_segment = AudioSegment(
        y.tobytes(),
        frame_rate=sr,
        sample_width=4,  # 4 bytes for 32-bit PCM
        channels=1,  # Mono
    )
    return audio_segment


def load_audio(file_path: str) -> tuple[np.ndarray, int]:
    y, sample_rate = librosa.load(file_path, sr=None)  # Load with 44.1kHz sample rate
    return y, sample_rate


def detect_bpm(y: np.ndarray, sample_rate: int) -> float:
    """Detect BPM of audio using multiple methods for better accuracy."""
    # Process only first 30 seconds of audio to save memory
    duration = 30  # seconds
    samples = min(len(y), int(sample_rate * duration))
    y = y[:samples]

    # Method 1: Standard beat tracking with parameters optimized for electronic music
    tempo1, _ = librosa.beat.beat_track(
        y=y,
        sr=sample_rate,
        start_bpm=126,  # Start with common electronic music BPM
        tightness=400,  # Increase tightness for electronic beats
        hop_length=512,  # Increased hop length to reduce memory usage
    )

    # Method 2: Use onset strength signal with memory-efficient settings
    onset_env = librosa.onset.onset_strength(
        y=y,
        sr=sample_rate,
        hop_length=512,  # Increased hop length
        aggregate=np.median,
    )

    # Apply peak picking to onset envelope
    onset_times = librosa.onset.onset_detect(
        onset_envelope=onset_env,
        sr=sample_rate,
        hop_length=512,
        post_max=30,  # Only post_max is retained
    )

    tempo2 = float(
        librosa.feature.tempo(  # Updated to new location
            onset_envelope=onset_env, sr=sample_rate, hop_length=512
        )[0]
    )

    # Method 3: Use dynamic programming beat tracker
    tempo3, _ = librosa.beat.beat_track(
        y=y, sr=sample_rate, start_bpm=126, units="time", hop_length=512, tightness=500
    )

    # Convert all tempos to float
    tempo1 = float(tempo1)
    tempo3 = float(tempo3)

    # Apply proximity weighting - give more weight to values closer to 126
    weights = [
        1 / (abs(126 - tempo1) + 1),
        1 / (abs(126 - tempo2) + 1),
        1 / (abs(126 - tempo3) + 1),
    ]

    # Normalize weights
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    # Calculate weighted average using proximity weights
    weighted_tempo = tempo1 * weights[0] + tempo2 * weights[1] + tempo3 * weights[2]

    logger.info(
        f"BPM Detection Results - Method 1: {tempo1:.1f}, Method 2: {tempo2:.1f}, Method 3: {tempo3:.1f}"
    )
    logger.info(f"Weights: {[f'{w:.3f}' for w in weights]}")
    logger.info(f"Final weighted BPM: {weighted_tempo:.1f}")

    return weighted_tempo


def time_stretch(y: np.ndarray, current_tempo: int, target_tempo: int) -> np.ndarray:
    # stretch_factor = target_tempo / current_tempo  # This is the correct formula
    stretch_factor = float(target_tempo) / float(current_tempo)
    y_stretched = librosa.effects.time_stretch(y=y, rate=stretch_factor)
    return y_stretched


def crossfade(
    song1: np.ndarray, song2: np.ndarray, sample_rate1: int, sample_rate2: int
) -> AudioSegment:
    """Overlay two songs, starting the second song 8 beats before the end of the first."""
    # Get beat positions
    _, beats1 = librosa.beat.beat_track(y=song1, sr=sample_rate1)
    _, beats2 = librosa.beat.beat_track(y=song2, sr=sample_rate2)

    # Convert beat frames to times (in ms)
    beat_times1 = librosa.frames_to_time(beats1, sr=sample_rate1) * 1000

    # Calculate average beat duration
    if len(beat_times1) > 1:
        avg_beat_duration = np.mean(np.diff(beat_times1))
    else:
        avg_beat_duration = 500  # fallback value in ms

    # Calculate the time position 8 beats from the end, minus half a beat
    if len(beat_times1) > 8:
        overlay_start_time = beat_times1[-8] - (
            avg_beat_duration / 2
        )  # Subtract half beat duration
    else:
        # Fallback if we don't have enough beats
        overlay_start_time = (len(song1) / sample_rate1 * 1000) - 4000

    # Align beats before converting to AudioSegment
    song1_aligned, song2_aligned = align_beats(song1, sample_rate1, song2, sample_rate2)

    # Convert numpy arrays to AudioSegment
    song1_segment = numpy_to_audiosegment(song1_aligned, sample_rate1)
    song2_segment = numpy_to_audiosegment(song2_aligned, sample_rate2)

    # Calculate required length for song1
    required_length = int(overlay_start_time + len(song2_segment))

    # Extend song1 if needed
    if len(song1_segment) < required_length:
        silence = AudioSegment.silent(duration=required_length - len(song1_segment))
        song1_segment = song1_segment + silence

    # Convert overlay_start_time from ms to seconds for logging
    overlay_start_seconds = overlay_start_time / 1000
    minutes = int(overlay_start_seconds // 60)
    seconds = int(overlay_start_seconds % 60)
    logger.info(f"Starting overlay at {minutes}:{seconds:02d}")
    logger.info(f"Average beat duration: {avg_beat_duration:.2f}ms")
    logger.info(f"Half beat offset: {avg_beat_duration/2:.2f}ms")

    # Overlay the songs
    mixed = song1_segment.overlay(song2_segment, position=int(overlay_start_time))

    # Extract 5 seconds before and 10 seconds after the transition
    before_transition = 5000  # 5 seconds in milliseconds
    after_transition = 10000  # 10 seconds in milliseconds
    transition_start = int(overlay_start_time - before_transition)
    transition_end = int(overlay_start_time + after_transition)

    # Ensure we don't try to extract before the start of the audio
    transition_start = max(0, transition_start)

    # Extract the transition portion
    transition_segment = mixed[transition_start:transition_end]

    logger.info(
        f"Extracted transition from {transition_start/1000:.1f}s to {transition_end/1000:.1f}s"
    )

    return transition_segment


def save_audio(audio_segment: AudioSegment, output_path: str) -> None:
    # Save as 32-bit float WAV
    audio_segment.export(
        output_path,
        format="wav",
        parameters=["-f", "float32"],  # Force 32-bit float format
    )


# Paths to input songs
song1_path = f"{MUSIC_DIR}/Sete - Nitefreak Remix BLOND_ISH, Francis Mercier, Amadou & Mariam, Nitefreak Sete (Nitefreak Remix) 2022.wav"
song2_path = f"{MUSIC_DIR}/Jamming - FISHER Rework Bob Marley & The Wailers, FISHER Jamming (FISHER Rework) 2024.wav"

# Load songs
song1, sample_rate1 = load_audio(song1_path)
song2, sample_rate2 = load_audio(song2_path)

# After loading the songs
logger.info(f"Song 1 sample rate: {sample_rate1}")
logger.info(f"Song 2 sample rate: {sample_rate2}")

# Synchronize BPM

song1_tempo = detect_bpm(song1, sample_rate1)
song2_tempo = detect_bpm(song2, sample_rate2)


target_bpm = min(song1_tempo, song2_tempo)
logger.info(f"Target BPM: {target_bpm}")
logger.info(f"Song 1 BPM: {song1_tempo}")
logger.info(f"Song 2 BPM: {song2_tempo}")

# Initialize synced songs
song1_synced = song1
song2_synced = song2

# Stretch each song if its tempo doesn't match target
if song1_tempo != target_bpm:
    logger.info(f"Stretching song 1 from {song1_tempo} to {target_bpm} BPM")
song1_synced = time_stretch(song1, song1_tempo, target_bpm)

if song2_tempo != target_bpm:
    logger.info(f"Stretching song 2 from {song2_tempo} to {target_bpm} BPM")
song2_synced = time_stretch(song2, song2_tempo, target_bpm)

# After BPM synchronization
song1_aligned, song2_aligned = align_beats(
    song1_synced, sample_rate1, song2_synced, sample_rate2
)

# Crossfade songs
mixed_audio = crossfade(song1_aligned, song2_aligned, sample_rate1, sample_rate2)

# Save the mixed output
output_path = "mixed_song.wav"
save_audio(mixed_audio, output_path)

logger.info(f"Mixed song saved at: {output_path}")
