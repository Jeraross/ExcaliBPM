"""
Detecção de BPM otimizada para mixagem.

Usa o sinal percussivo isolado para onset envelope mais limpo,
com normalização para a faixa 60-180 BPM usada em DJ.
"""

import numpy as np
import librosa


def detectar_bpm(
    y: np.ndarray,
    sr: int,
    y_percussive: np.ndarray | None = None,
) -> float:
    """
    Detecta BPM a partir do sinal de áudio.

    Se y_percussive for fornecido, usa-o para onset envelope
    (mais preciso por ignorar conteúdo harmônico).
    """
    sinal = y_percussive if y_percussive is not None else y
    onset_env = librosa.onset.onset_strength(y=sinal, sr=sr)

    # prior=None deixa o librosa estimar sem viés
    bpm_arr = librosa.feature.tempo(
        onset_envelope=onset_env,
        sr=sr,
        aggregate=None,  # retorna múltiplas estimativas
    )

    if len(bpm_arr) == 0:
        return 0.0

    # Pega a estimativa mais frequente (moda)
    # Se aggregate=None retorna array de estimativas ao longo do tempo
    if bpm_arr.ndim > 0 and len(bpm_arr) > 1:
        # Arredonda para inteiro e pega a moda
        bpm_rounded = np.round(bpm_arr).astype(int)
        values, counts = np.unique(bpm_rounded, return_counts=True)
        bpm = float(values[np.argmax(counts)])
    else:
        bpm = float(bpm_arr[0]) if hasattr(bpm_arr, '__len__') else float(bpm_arr)

    # Normaliza para faixa útil de DJ (60-180 BPM)
    while bpm < 60:
        bpm *= 2
    while bpm > 180:
        bpm /= 2

    return round(bpm, 1)
