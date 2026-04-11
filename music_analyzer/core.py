"""
Orquestrador principal da análise musical.

Coordena todos os módulos (chroma, key_detect, bpm, camelot) para
produzir uma análise completa e robusta de uma faixa de áudio.
"""

import numpy as np
import librosa
import concurrent.futures

from .chroma import pipeline_chroma
from .key_detect import (
    ensemble_votar,
    votacao_por_frames,
    analisar_bass_register,
    desambiguar_resultado,
)
from .bpm import detectar_bpm
from .models import AnaliseMusical


def analisar_musica(
    caminho_audio: str,
    duracao_trecho: float = 30.0,
    sr: int = 22050,
) -> AnaliseMusical:
    """
    Análise completa de uma faixa de áudio.

    Pipeline:
    1. Carrega áudio e separa harmônico/percussivo
    2. Extrai cromagrama CQT+CENS com filtragem e ponderação
    3. Detecta tonalidade via ensemble de 8 perfis
    4. Votação frame-a-frame para robustez
    5. Análise de endpoints (início e fim)
    6. Análise de registro grave para desambiguação
    7. Combinação de todas as evidências
    8. Detecção de BPM via sinal percussivo

    Parâmetros
    ----------
    caminho_audio : str
        Caminho para o arquivo (wav, mp3, flac, ogg, etc.)
    duracao_trecho : float
        Segundos para análise de início/fim (padrão: 30s)
    sr : int
        Taxa de amostragem (22050 é suficiente para análise tonal)
    """
    # ── 1. Carrega o áudio ───────────────────────────────────────
    y, sr = librosa.load(caminho_audio, sr=sr)
    duracao = librosa.get_duration(y=y, sr=sr)

    # ── 2. Separação harmônica/percussiva ────────────────────────
    y_harmonic, y_percussive = librosa.effects.hpss(y)

    # ── 3. Pipeline de chroma (CQT + CENS) ──────────────────────
    chroma_data = pipeline_chroma(y, sr, hop_length=512)
    chroma_cqt = chroma_data["cqt"]
    chroma_cens = chroma_data["cens"]

    # RMS para filtragem de silêncio na votação por frames
    rms = librosa.feature.rms(y=y, hop_length=512)[0]

    # ── 4. Fatiamento dos trechos de início e fim ────────────────
    max_trecho = min(duracao_trecho, duracao * 0.3)
    frames_trecho = int(max_trecho * sr / 512)

    chroma_inicio = chroma_cqt[:, :frames_trecho]
    chroma_final = chroma_cqt[:, -frames_trecho:]

    # ── 5. Análise concorrente ───────────────────────────────────
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        # BPM (usa percussivo)
        fut_bpm = executor.submit(detectar_bpm, y, sr, y_percussive)

        # Ensemble global (CQT)
        media_cqt = np.mean(chroma_cqt, axis=1)
        fut_global_cqt = executor.submit(ensemble_votar, media_cqt)

        # Ensemble global (CENS) — segundo votante
        media_cens = np.mean(chroma_cens, axis=1)
        fut_global_cens = executor.submit(ensemble_votar, media_cens)

        # Votação por frames
        fut_frames = executor.submit(
            votacao_por_frames, chroma_cqt, sr, 512, 4.0, rms
        )

        # Endpoints
        media_inicio = np.mean(chroma_inicio, axis=1)
        fut_inicio = executor.submit(ensemble_votar, media_inicio)

        media_final = np.mean(chroma_final, axis=1)
        fut_final = executor.submit(ensemble_votar, media_final)

        # Bass register
        y_harm_full = chroma_data["y_harmonic"]
        fut_bass = executor.submit(analisar_bass_register, y_harm_full, sr, 512)

        # Coleta resultados
        bpm = fut_bpm.result()
        res_global_cqt = fut_global_cqt.result()
        res_global_cens = fut_global_cens.result()
        res_frames = fut_frames.result()
        res_inicio = fut_inicio.result()
        res_final = fut_final.result()
        chroma_bass = fut_bass.result()

    # ── 6. Meta-ensemble: combina CQT e CENS ────────────────────
    # Se CQT e CENS concordam, confiança alta.
    # Se discordam, a votação por frames decide.
    if res_global_cqt.tom == res_global_cens.tom:
        res_global = res_global_cqt
        res_global.confianca = min(1.0, res_global.confianca * 1.2)
    elif res_global_cqt.tom == res_frames.tom:
        res_global = res_global_cqt
    elif res_global_cens.tom == res_frames.tom:
        res_global = res_global_cens
    else:
        # Nenhum acordo — usa CQT como principal
        res_global = res_global_cqt

    # ── 7. Desambiguação final ───────────────────────────────────
    resultado = desambiguar_resultado(
        resultado_global=res_global,
        resultado_frames=res_frames,
        resultado_inicio=res_inicio,
        resultado_final=res_final,
        chroma_bass=chroma_bass,
    )

    # ── 8. Monta resultado final ─────────────────────────────────
    return AnaliseMusical(
        tonalidade_geral=resultado.tom,
        confianca_geral=resultado.confianca,
        tonalidade_inicio=res_inicio.tom,
        confianca_inicio=res_inicio.confianca,
        tonalidade_final=res_final.tom,
        confianca_final=res_final.confianca,
        bpm=bpm,
        duracao_segundos=duracao,
        arquivo=caminho_audio,
        votos_perfis=resultado.votos_perfis,
        votos_frames=resultado.votos_frames or [],
    )


def analisar_lote(
    caminhos: list[str],
    sr: int = 22050,
) -> list[AnaliseMusical]:
    """
    Analisa múltiplas faixas sequencialmente.

    Para paralelismo real entre faixas, use ProcessPoolExecutor
    externamente (cada faixa já usa threads internamente).
    """
    resultados = []
    for caminho in caminhos:
        try:
            r = analisar_musica(caminho, sr=sr)
            resultados.append(r)
        except Exception as e:
            print(f"  ERRO em {caminho}: {e}")
    return resultados
