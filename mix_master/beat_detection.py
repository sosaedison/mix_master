MUSIC_DIR = "music"
import numpy as np
import librosa
import scipy.signal
from pprint import pprint


def custom_bpm_detector(y, sr):
    """Highly tuned BPM detection for house music (115–130 BPM)."""
    
    # Ensure sufficient audio length
    if len(y) < sr * 5:
        raise ValueError("Audio too short for BPM detection.")
    
    # Convert to mono and apply pre-emphasis
    y = librosa.to_mono(y)
    y_filtered = librosa.effects.preemphasis(y, coef=0.97)
    
    # Downsample to focus on rhythmic content
    y_ds = librosa.resample(y_filtered, orig_sr=sr, target_sr=sr // 2)
    sr_ds = sr // 2
    
    # Onset envelope detection with strong smoothing
    onset_env = librosa.onset.onset_strength(y=y_ds, sr=sr_ds, aggregate=np.mean)
    onset_env_smooth = scipy.signal.savgol_filter(onset_env, window_length=51, polyorder=3)
    onset_env_smooth = librosa.util.normalize(onset_env_smooth)

    # Autocorrelation with more smoothing
    autocorr = np.correlate(onset_env_smooth, onset_env_smooth, mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    autocorr = scipy.signal.medfilt(autocorr, kernel_size=7)
    
    print(f"Autocorrelation length: {len(autocorr)}")
    
    # Lag to BPM conversion within 115–130 BPM
    bpm_min, bpm_max = 115, 130
    lag_min = int(sr_ds * 60 / bpm_max)
    lag_max = int(sr_ds * 60 / bpm_min)
    
    # Ensure valid lag range by adjusting to autocorrelation length
    if lag_max > len(autocorr):
        print(f"Adjusting lag range as the original lag_max {lag_max} exceeds autocorrelation length.")
        lag_max = len(autocorr)  # Limit lag_max to the autocorrelation length

    if lag_min > len(autocorr):
        print(f"Adjusting lag_min {lag_min} to fit within autocorrelation length.")
        lag_min = len(autocorr) // 2  # Set lag_min to the middle of the autocorrelation
    
    # Ensure lag_min and lag_max are within bounds
    if lag_min >= len(autocorr) or lag_max > len(autocorr):
        raise ValueError("Lag range exceeds autocorrelation length after adjustment. Audio may not have enough rhythmic content.")
    
    print(f"Adjusted Lag range -> min: {lag_min}, max: {lag_max}")
    
    # Slice the autocorrelation to focus on our BPM range
    autocorr_slice = autocorr[lag_min:lag_max]
    if len(autocorr_slice) == 0:
        raise ValueError("Autocorrelation slice is empty. Audio may lack rhythmic content or be too short.")
    
    # Check if we have valid peaks
    peaks, properties = scipy.signal.find_peaks(autocorr_slice, height=np.max(autocorr_slice) * 0.8)
    
    if len(peaks) == 0:
        raise ValueError("No dominant peaks detected. Try a louder or clearer track.")
    
    # Select the strongest peak
    peak_lag = peaks[np.argmax(properties['peak_heights'])] + lag_min
    estimated_bpm = 60 / (peak_lag / sr_ds)
    
    # Correct BPM for over/under estimation
    bpm_candidates = [estimated_bpm, estimated_bpm / 2, estimated_bpm * 2]
    corrected_bpm = min(bpm_candidates, key=lambda bpm: abs(bpm - 125))
    
    print(f"BPM Candidates: {bpm_candidates}")
    print(f"Corrected BPM: {corrected_bpm}")
    
    # Updated sanity check with librosa's latest tempo function
    tempo_librosa = librosa.feature.rhythm.tempo(y=y, sr=sr, start_bpm=125, aggregate=None)
    print(f"Librosa Estimated Tempo: {tempo_librosa[0]}")
    
    return round(corrected_bpm)


def main():
    # Load audio file
    # Paths to input songs
    song1_path = f"{MUSIC_DIR}/Sete - Nitefreak Remix BLOND_ISH, Francis Mercier, Amadou & Mariam, Nitefreak Sete (Nitefreak Remix) 2022.wav"
    song2_path = f"{MUSIC_DIR}/Jamming - FISHER Rework Bob Marley & The Wailers, FISHER Jamming (FISHER Rework) 2024.wav"

    songs = [song1_path, song2_path]

    for file_path in songs:
        y, sr = librosa.load(file_path, sr=None)
        print(pprint(y))

        # Detect BPM
        bpm = custom_bpm_detector(y, sr)
        print(f"Estimated BPM: {bpm}")


if __name__ == "__main__":
    main()
