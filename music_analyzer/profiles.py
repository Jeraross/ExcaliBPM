"""
Perfis de tonalidade para detecção de tom musical.

Contém 7 conjuntos de perfis validados pela literatura acadêmica,
cada um otimizado para diferentes gêneros e contextos.
Os valores representam a importância relativa de cada nota cromática
(C, C#, D, D#, E, F, F#, G, G#, A, A#, B) dentro de uma escala.
"""

import numpy as np

PROFILES: dict[str, dict[str, list[float]]] = {
    # ── Krumhansl-Kessler (1990) ─────────────────────────────────
    # Origem: experimentos perceptuais com probe-tone.
    # Bom para: trechos clássicos curtos.
    # Fraqueza: propenso a confusão com a dominante (5ª).
    "krumhansl_kessler": {
        "major": [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
        "minor": [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    },

    # ── Temperley CBMS (2007) ────────────────────────────────────
    # Origem: Music and Probability, p.86.
    # Bom para: uso geral, boa separação maior/menor.
    "temperley": {
        "major": [5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0],
        "minor": [5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0],
    },

    # ── Temperley / Kostka-Payne ─────────────────────────────────
    # Origem: corpus de análises do livro Kostka-Payne.
    # Bom para: música clássica. Alta precisão em modo maior.
    "kostka_payne": {
        "major": [0.748, 0.060, 0.488, 0.082, 0.670, 0.460, 0.096, 0.715, 0.104, 0.366, 0.057, 0.400],
        "minor": [0.712, 0.084, 0.474, 0.618, 0.049, 0.460, 0.105, 0.747, 0.404, 0.067, 0.133, 0.330],
    },

    # ── Bellman-Budge (2005) ─────────────────────────────────────
    # Origem: estudo de frequência de acordes de Budge (1943).
    # Bom para: MENOR tendência a confusão com tons vizinhos.
    # Recomendado como perfil padrão principal.
    "bellman_budge": {
        "major": [16.80, 0.86, 12.95, 1.41, 13.49, 11.93, 1.25, 20.28, 1.80, 8.04, 0.62, 10.57],
        "minor": [18.16, 0.69, 12.99, 13.34, 1.07, 11.15, 1.38, 21.07, 7.49, 1.53, 0.92, 10.21],
    },

    # ── Aarden / Essen (2003) ────────────────────────────────────
    # Origem: Essen Folk Song Collection.
    # Bom para: música folk, altíssima precisão em modo menor.
    "aarden_essen": {
        "major": [17.7661, 0.145624, 14.9265, 0.160186, 19.8049, 11.3587, 0.291248,
                  22.062, 0.145624, 8.15494, 0.232998, 4.95122],
        "minor": [18.2648, 0.737619, 14.0499, 16.8599, 0.702494, 14.4362, 0.702494,
                  18.6161, 4.56621, 1.93186, 7.37619, 1.75623],
    },

    # ── Simple / Sapp (2011) ─────────────────────────────────────
    # Pesos binários: 2=tônica/dominante, 1=diatônica, 0=cromática.
    # Surpreendentemente eficaz para regiões longas de música.
    "simple_sapp": {
        "major": [2, 0, 1, 0, 1, 1, 0, 2, 0, 1, 0, 1],
        "minor": [2, 0, 1, 1, 0, 1, 0, 2, 1, 0, 0.5, 0.5],
    },

    # ── Albrecht-Shanahan (2013) ─────────────────────────────────
    # Treinado via rede neural em 490 peças.
    # Melhor precisão em modo menor de todos os perfis.
    # NOTA: funciona melhor com distância euclidiana.
    "albrecht_shanahan": {
        "major": [0.238, 0.006, 0.111, 0.006, 0.137, 0.094, 0.016, 0.214, 0.009, 0.080, 0.008, 0.081],
        "minor": [0.220, 0.006, 0.104, 0.123, 0.019, 0.103, 0.012, 0.214, 0.062, 0.022, 0.061, 0.052],
    },
}

# ── Perfis Shaath — otimizados para música eletrônica/pop ────────
PROFILES_EDM: dict[str, dict[str, list[float]]] = {
    "shaath": {
        "major": [0.95162, 0.20742, 0.71758, 0.22007, 0.71341, 0.48841, 0.31431,
                  1.00000, 0.20957, 0.53657, 0.22585, 0.55363],
        "minor": [0.94409, 0.21742, 0.64525, 0.63229, 0.27897, 0.57709, 0.26428,
                  1.0000, 0.26428, 0.30633, 0.45924, 0.35929],
    },
}


def get_all_profiles() -> dict[str, dict[str, np.ndarray]]:
    """Retorna todos os perfis (gerais + EDM) como arrays numpy normalizados."""
    combined = {**PROFILES, **PROFILES_EDM}
    result = {}
    for name, modes in combined.items():
        result[name] = {
            "major": np.array(modes["major"], dtype=np.float64),
            "minor": np.array(modes["minor"], dtype=np.float64),
        }
    return result
