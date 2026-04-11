"""
Modelos de dados para resultados de análise musical.
"""

from dataclasses import dataclass, field
from .camelot import obter_camelot, obter_openkey


@dataclass
class AnaliseMusical:
    """Resultado completo da análise de uma faixa."""

    # Tonalidade geral
    tonalidade_geral: str
    confianca_geral: float

    # Tonalidade no início
    tonalidade_inicio: str
    confianca_inicio: float

    # Tonalidade no final
    tonalidade_final: str
    confianca_final: float

    # BPM
    bpm: float

    # Metadados
    duracao_segundos: float
    arquivo: str = ""

    # Detalhes dos votos (para debug)
    votos_perfis: dict[str, str] = field(default_factory=dict)
    votos_frames: list[str] = field(default_factory=list)

    @property
    def camelot(self) -> str:
        return obter_camelot(self.tonalidade_geral) or "?"

    @property
    def openkey(self) -> str:
        return obter_openkey(self.tonalidade_geral) or "?"

    @property
    def camelot_inicio(self) -> str:
        return obter_camelot(self.tonalidade_inicio) or "?"

    @property
    def camelot_final(self) -> str:
        return obter_camelot(self.tonalidade_final) or "?"

    def __str__(self) -> str:
        minutos = int(self.duracao_segundos // 60)
        segundos = int(self.duracao_segundos % 60)

        linhas = [
            f"{'═' * 56}",
            f"  ANÁLISE MUSICAL",
            f"  {self.arquivo}" if self.arquivo else "",
            f"{'═' * 56}",
            f"  Duração        : {minutos}:{segundos:02d}",
            f"  BPM            : {self.bpm:.1f}",
            f"{'─' * 56}",
            f"  Tom Geral      : {self.tonalidade_geral:<14} │ {self.camelot:<4} │ {self.confianca_geral:.0%}",
            f"  Tom Início     : {self.tonalidade_inicio:<14} │ {self.camelot_inicio:<4} │ {self.confianca_inicio:.0%}",
            f"  Tom Final      : {self.tonalidade_final:<14} │ {self.camelot_final:<4} │ {self.confianca_final:.0%}",
            f"{'═' * 56}",
        ]
        return "\n".join(l for l in linhas if l)

    def to_dict(self) -> dict:
        """Serialização para JSON."""
        return {
            "arquivo": self.arquivo,
            "duracao_segundos": round(self.duracao_segundos, 2),
            "bpm": self.bpm,
            "tonalidade_geral": self.tonalidade_geral,
            "camelot": self.camelot,
            "openkey": self.openkey,
            "confianca_geral": round(self.confianca_geral, 4),
            "tonalidade_inicio": self.tonalidade_inicio,
            "camelot_inicio": self.camelot_inicio,
            "confianca_inicio": round(self.confianca_inicio, 4),
            "tonalidade_final": self.tonalidade_final,
            "camelot_final": self.camelot_final,
            "confianca_final": round(self.confianca_final, 4),
        }
