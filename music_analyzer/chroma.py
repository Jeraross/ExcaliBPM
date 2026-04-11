"""
Pipeline de extração de cromagrama otimizado para detecção de tonalidade.

Implementa as melhores práticas da literatura:
- Separação harmônica agressiva (HPSS margin=8)
- CQT com 36 bins/oitava (3 por semitom)
- Correção automática de afinação
- Filtragem não-local + mediana temporal
- Ponderação por energia (RMS)
"""

import numpy as np
import scipy.ndimage
import librosa


def extrair_harmonico(y: np.ndarray, margin: int = 8) -> np.ndarray:
    """
    Isola o conteúdo harmônico do áudio via HPSS.

    margin=8 é agressivo — suprime quase toda percussão e ruído,
    preservando melodia, acordes e linhas de baixo. Ideal para
    análise de tonalidade onde percussão polui o cromagrama.
    """
    return librosa.effects.harmonic(y=y, margin=margin)


def estimar_afinacao(y: np.ndarray, sr: int) -> float:
    """
    Estima o desvio de afinação do áudio em relação a A440.

    Muitas gravações estão levemente desafinadas (± 10-50 cents).
    Sem correção, a energia cromática vaza para bins adjacentes,
    reduzindo a precisão da detecção de tom.
    """
    return librosa.estimate_tuning(y=y, sr=sr, n_fft=8192)


def extrair_chroma_cqt(
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
    tuning: float | None = None,
) -> np.ndarray:
    """
    Extrai cromagrama via Constant-Q Transform com parâmetros otimizados.

    bins_per_octave=36 (3 bins/semitom) melhora significativamente a
    resolução em baixas frequências, reduzindo vazamento de energia
    entre notas próximas — especialmente entre tônica e dominante.
    """
    if tuning is None:
        tuning = estimar_afinacao(y, sr)

    chroma = librosa.feature.chroma_cqt(
        y=y,
        sr=sr,
        hop_length=hop_length,
        fmin=librosa.note_to_hz("C1"),
        n_chroma=12,
        n_octaves=7,
        bins_per_octave=36,
        norm=np.inf,
        tuning=tuning,
    )
    return chroma


def extrair_chroma_cens(
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> np.ndarray:
    """
    Extrai cromagrama CENS — mais robusto a variações de timbre
    e qualidade de gravação, porém menos preciso para distinguir
    tônica de dominante. Usado como segundo votante no ensemble.
    """
    return librosa.feature.chroma_cens(y=y, sr=sr, hop_length=hop_length)


def filtrar_chroma(chroma: np.ndarray) -> np.ndarray:
    """
    Aplica filtragem em dois estágios:

    1. Non-local filtering (nn_filter): suprime ruídos esparsos
       comparando cada frame com vizinhos via similaridade cosseno.
    2. Mediana temporal (kernel 9): suaviza flutuações rápidas
       preservando bordas (transições de acorde).
    """
    chroma_filtrado = np.minimum(
        chroma,
        librosa.decompose.nn_filter(
            chroma, aggregate=np.median, metric="cosine"
        ),
    )
    chroma_filtrado = scipy.ndimage.median_filter(chroma_filtrado, size=(1, 9))
    return chroma_filtrado


def ponderar_por_energia(
    chroma: np.ndarray,
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> np.ndarray:
    """
    Pondera cada frame do cromagrama pela energia RMS do áudio.

    Garante que trechos altos (refrão, drops) contribuam mais para
    a estimativa de tom do que intros silenciosas ou bridges suaves.
    """
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    n = min(chroma.shape[1], len(rms))
    return chroma[:, :n] * rms[:n][np.newaxis, :]


def pipeline_chroma(
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> dict[str, np.ndarray]:
    """
    Pipeline completo de extração de cromagrama.

    Retorna um dicionário com:
    - 'cqt': chroma CQT filtrado e ponderado (principal)
    - 'cens': chroma CENS ponderado (secundário para ensemble)
    - 'y_harmonic': sinal harmônico isolado
    - 'tuning': desvio de afinação estimado
    """
    # 1. Separação harmônica agressiva
    y_harmonic = extrair_harmonico(y, margin=8)

    # 2. Estimativa de afinação
    tuning = estimar_afinacao(y_harmonic, sr)

    # 3. Chroma CQT (principal)
    chroma_cqt = extrair_chroma_cqt(y_harmonic, sr, hop_length, tuning)
    chroma_cqt = filtrar_chroma(chroma_cqt)
    chroma_cqt_w = ponderar_por_energia(chroma_cqt, y, sr, hop_length)

    # 4. Chroma CENS (votante secundário)
    chroma_cens = extrair_chroma_cens(y_harmonic, sr, hop_length)
    chroma_cens_w = ponderar_por_energia(chroma_cens, y, sr, hop_length)

    return {
        "cqt": chroma_cqt_w,
        "cens": chroma_cens_w,
        "cqt_raw": chroma_cqt,
        "y_harmonic": y_harmonic,
        "tuning": tuning,
    }
