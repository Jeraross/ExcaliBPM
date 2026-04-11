"""
Motor de detecção de tonalidade musical.

Combina múltiplas estratégias para máxima precisão:
1. Correlação de Pearson com 7 conjuntos de perfis
2. Votação por ensemble (maioria entre perfis)
3. Votação frame-a-frame (segmentos de ~4s)
4. Análise de endpoints (início/fim da música)
5. Análise de registro grave para desambiguação de tônica
"""

import numpy as np
from collections import Counter
from dataclasses import dataclass

from .profiles import get_all_profiles

NOTAS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Relações entre tons relativos (maior -> menor relativo)
_RELATIVOS = {
    "C Major": "A Minor", "G Major": "E Minor", "D Major": "B Minor",
    "A Major": "F# Minor", "E Major": "C# Minor", "B Major": "G# Minor",
    "F# Major": "D# Minor", "C# Major": "A# Minor", "G# Major": "F Minor",
    "D# Major": "C Minor", "A# Major": "G Minor", "F Major": "D Minor",
}
_RELATIVOS.update({v: k for k, v in _RELATIVOS.items()})


@dataclass
class ResultadoTonalidade:
    """Resultado detalhado da detecção de tonalidade."""
    tom: str
    confianca: float
    correlacoes: dict[str, float]
    votos_perfis: dict[str, str]
    votos_frames: list[str] | None = None


def _pearson_correlacao(x: np.ndarray, y: np.ndarray) -> float:
    """Correlação de Pearson entre dois vetores."""
    x_c = x - np.mean(x)
    y_c = y - np.mean(y)
    num = np.dot(x_c, y_c)
    den = np.linalg.norm(x_c) * np.linalg.norm(y_c)
    if den < 1e-12:
        return 0.0
    return num / den


def _euclidiana_similaridade(x: np.ndarray, y: np.ndarray) -> float:
    """Similaridade baseada em distância euclidiana (invertida)."""
    x_n = x / (np.linalg.norm(x) + 1e-12)
    y_n = y / (np.linalg.norm(y) + 1e-12)
    dist = np.linalg.norm(x_n - y_n)
    return 1.0 / (1.0 + dist)


def detectar_com_perfil(
    chroma_vec: np.ndarray,
    perfil_major: np.ndarray,
    perfil_minor: np.ndarray,
    usar_euclidiana: bool = False,
) -> tuple[str, float, dict[str, float]]:
    """
    Detecção K-S com um único par de perfis.

    Testa as 24 tonalidades possíveis (12 maiores + 12 menores)
    rotacionando os perfis e calculando a correlação com o cromagrama.
    """
    func = _euclidiana_similaridade if usar_euclidiana else _pearson_correlacao
    correlacoes: dict[str, float] = {}

    for i in range(12):
        maj_rot = np.roll(perfil_major, i)
        min_rot = np.roll(perfil_minor, i)

        correlacoes[f"{NOTAS[i]} Major"] = func(chroma_vec, maj_rot)
        correlacoes[f"{NOTAS[i]} Minor"] = func(chroma_vec, min_rot)

    ranking = sorted(correlacoes.items(), key=lambda x: x[1], reverse=True)
    melhor_tom, melhor_corr = ranking[0]
    segundo_corr = ranking[1][1]

    # Confiança: distância relativa entre 1º e 2º lugar
    gap = melhor_corr - segundo_corr
    confianca = min(1.0, max(0.0, gap / (abs(melhor_corr) + 1e-10) * 3.0))

    return melhor_tom, confianca, correlacoes


def ensemble_votar(
    chroma_vec: np.ndarray,
    perfis: dict[str, dict[str, np.ndarray]] | None = None,
) -> ResultadoTonalidade:
    """
    Votação por ensemble: cada conjunto de perfis vota independentemente,
    o tom mais votado vence. Em caso de empate, usa a maior correlação média.
    """
    if perfis is None:
        perfis = get_all_profiles()

    votos: list[str] = []
    votos_por_perfil: dict[str, str] = {}
    todas_correlacoes: dict[str, list[float]] = {}

    for nome, modos in perfis.items():
        usar_euc = nome == "albrecht_shanahan"
        tom, conf, corrs = detectar_com_perfil(
            chroma_vec, modos["major"], modos["minor"], usar_euclidiana=usar_euc
        )
        votos.append(tom)
        votos_por_perfil[nome] = tom

        for k, v in corrs.items():
            todas_correlacoes.setdefault(k, []).append(v)

    # Correlação média para cada tom (usado em desempate)
    media_corr = {k: np.mean(v) for k, v in todas_correlacoes.items()}

    contagem = Counter(votos)
    max_votos = contagem.most_common(1)[0][1]
    empatados = [t for t, c in contagem.items() if c == max_votos]

    if len(empatados) == 1:
        vencedor = empatados[0]
    else:
        # Desempate pela maior correlação média
        vencedor = max(empatados, key=lambda t: media_corr.get(t, 0))

    # Confiança do ensemble: proporção de votos do vencedor
    confianca = max_votos / len(votos)

    return ResultadoTonalidade(
        tom=vencedor,
        confianca=confianca,
        correlacoes=media_corr,
        votos_perfis=votos_por_perfil,
    )


def votacao_por_frames(
    chroma: np.ndarray,
    sr: int,
    hop_length: int = 512,
    duracao_segmento: float = 4.0,
    rms: np.ndarray | None = None,
    limiar_silencio: float = 0.01,
) -> ResultadoTonalidade:
    """
    Divide o cromagrama em segmentos de ~4s, detecta o tom de cada um
    e faz votação por maioria. Descarta segmentos silenciosos.

    Mais robusto que a média global porque modulações ou bridges
    longos não distorcem o resultado.
    """
    frames_por_seg = int(duracao_segmento * sr / hop_length)
    total_frames = chroma.shape[1]
    perfis = get_all_profiles()

    votos: list[str] = []

    for inicio in range(0, total_frames - frames_por_seg // 2, frames_por_seg):
        fim = min(inicio + frames_por_seg, total_frames)
        seg = chroma[:, inicio:fim]

        # Filtra silêncio
        if rms is not None:
            rms_seg = rms[inicio:min(fim, len(rms))]
            if len(rms_seg) > 0 and np.mean(rms_seg) < limiar_silencio:
                continue

        chroma_medio = np.mean(seg, axis=1)
        if np.linalg.norm(chroma_medio) < 1e-10:
            continue

        resultado = ensemble_votar(chroma_medio, perfis)
        votos.append(resultado.tom)

    if not votos:
        return ResultadoTonalidade(
            tom="Indeterminado", confianca=0.0,
            correlacoes={}, votos_perfis={}, votos_frames=votos,
        )

    contagem = Counter(votos)
    vencedor, n_votos = contagem.most_common(1)[0]
    confianca = n_votos / len(votos)

    return ResultadoTonalidade(
        tom=vencedor, confianca=confianca,
        correlacoes={}, votos_perfis={}, votos_frames=votos,
    )


def analisar_bass_register(
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> np.ndarray:
    """
    Extrai cromagrama apenas do registro grave (< ~300 Hz).

    A nota mais frequente no baixo em pontos cadenciais é muito
    provavelmente a tônica. Ajuda a desambiguar C Major vs A Minor.
    """
    # Filtra frequências acima de 300 Hz com passa-baixa
    import librosa

    # Usa CQT limitado ao registro grave (C1 a D#3 ≈ 32-311 Hz)
    S = np.abs(librosa.cqt(
        y=y, sr=sr, hop_length=hop_length,
        fmin=librosa.note_to_hz("C1"),
        n_bins=36,  # 3 oitavas × 12 bins
        bins_per_octave=12,
    ))

    # Mapeia para 12 classes de altura (chroma do baixo)
    chroma_bass = np.zeros((12, S.shape[1]))
    for i in range(S.shape[0]):
        chroma_bass[i % 12] += S[i]

    return chroma_bass


def desambiguar_resultado(
    resultado_global: ResultadoTonalidade,
    resultado_frames: ResultadoTonalidade,
    resultado_inicio: ResultadoTonalidade,
    resultado_final: ResultadoTonalidade,
    chroma_bass: np.ndarray | None = None,
) -> ResultadoTonalidade:
    """
    Combina todas as evidências para produzir o resultado final.

    Pesos:
    - Ensemble global: 3 votos
    - Votação por frames: 3 votos
    - Início da música: 1 voto
    - Final da música: 2 votos (fim é mais forte indicador de tônica)
    - Baixo: 1 voto (se disponível)
    """
    votos_pesados: list[str] = []

    votos_pesados.extend([resultado_global.tom] * 3)
    votos_pesados.extend([resultado_frames.tom] * 3)
    votos_pesados.extend([resultado_inicio.tom] * 1)
    votos_pesados.extend([resultado_final.tom] * 2)

    # Análise do baixo como desempate
    if chroma_bass is not None:
        bass_sum = np.sum(chroma_bass, axis=1)
        nota_bass_idx = int(np.argmax(bass_sum))
        # Vota no tom que tem essa nota como tônica
        votos_pesados.append(f"{NOTAS[nota_bass_idx]} Major")
        votos_pesados.append(f"{NOTAS[nota_bass_idx]} Minor")

    contagem = Counter(votos_pesados)
    candidatos = contagem.most_common(4)

    vencedor = candidatos[0][0]
    total = sum(c for _, c in candidatos)
    confianca = candidatos[0][1] / total

    # Se os dois primeiros são relativos (ex: C Major e A Minor),
    # usa o baixo e os endpoints para decidir
    if len(candidatos) >= 2:
        segundo = candidatos[1][0]
        if _RELATIVOS.get(vencedor) == segundo or _RELATIVOS.get(segundo) == vencedor:
            # Verifica qual tônica aparece mais nos endpoints e no baixo
            pontos_v = 0
            pontos_s = 0

            # Endpoints favorecem o final (convenção tonal: terminar na tônica)
            if resultado_final.tom == vencedor:
                pontos_v += 2
            elif resultado_final.tom == segundo:
                pontos_s += 2

            if resultado_inicio.tom == vencedor:
                pontos_v += 1
            elif resultado_inicio.tom == segundo:
                pontos_s += 1

            # Baixo: a tônica deve ser a nota mais proeminente no registro grave
            if chroma_bass is not None:
                bass_sum = np.sum(chroma_bass, axis=1)
                tonica_v = NOTAS.index(vencedor.split()[0])
                tonica_s = NOTAS.index(segundo.split()[0])
                if bass_sum[tonica_v] > bass_sum[tonica_s]:
                    pontos_v += 1
                else:
                    pontos_s += 1

            if pontos_s > pontos_v:
                vencedor = segundo
                confianca = candidatos[1][1] / total

    # Combina correlações do resultado global
    resultado_final_r = ResultadoTonalidade(
        tom=vencedor,
        confianca=confianca,
        correlacoes=resultado_global.correlacoes,
        votos_perfis=resultado_global.votos_perfis,
        votos_frames=resultado_frames.votos_frames,
    )
    return resultado_final_r
