"""
Music Analyzer — Detecção robusta de tonalidade e BPM para mixagem.

Uso rápido:
    from music_analyzer import analisar_musica, compatibilidade, sugerir_proximas

    resultado = analisar_musica("track.wav")
    print(resultado)

    compat = compatibilidade(resultado.tonalidade_geral, "A Minor")
    print(compat)
"""

from .core import analisar_musica, analisar_lote
from .models import AnaliseMusical
from .camelot import compatibilidade, sugerir_proximas, obter_camelot, obter_openkey

__all__ = [
    "analisar_musica",
    "analisar_lote",
    "AnaliseMusical",
    "compatibilidade",
    "sugerir_proximas",
    "obter_camelot",
    "obter_openkey",
]

__version__ = "1.0.0"
