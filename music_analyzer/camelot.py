"""
Roda de Camelot para compatibilidade harmônica em mixagem.

O sistema Camelot codifica as 24 tonalidades em um código alfanumérico
(1A-12A para menores, 1B-12B para maiores) onde tons compatíveis estão
a ±1 posição na roda ou na mesma posição com letra diferente.
"""

# Mapeamento Tom Musical → Código Camelot
TOM_PARA_CAMELOT: dict[str, str] = {
    "C Major": "8B",   "G Major": "9B",   "D Major": "10B",  "A Major": "11B",
    "E Major": "12B",  "B Major": "1B",   "F# Major": "2B",  "C# Major": "3B",
    "G# Major": "4B",  "D# Major": "5B",  "A# Major": "6B",  "F Major": "7B",
    "A Minor": "8A",   "E Minor": "9A",   "B Minor": "10A",  "F# Minor": "11A",
    "C# Minor": "12A", "G# Minor": "1A",  "D# Minor": "2A",  "A# Minor": "3A",
    "F Minor": "4A",   "C Minor": "5A",   "G Minor": "6A",   "D Minor": "7A",
}

# Mapeamento inverso
CAMELOT_PARA_TOM: dict[str, str] = {v: k for k, v in TOM_PARA_CAMELOT.items()}

# Mapeamento Open Key (alternativa usada por alguns softwares)
TOM_PARA_OPENKEY: dict[str, str] = {
    "C Major": "1d",   "G Major": "2d",   "D Major": "3d",   "A Major": "4d",
    "E Major": "5d",   "B Major": "6d",   "F# Major": "7d",  "C# Major": "8d",
    "G# Major": "9d",  "D# Major": "10d", "A# Major": "11d", "F Major": "12d",
    "A Minor": "1m",   "E Minor": "2m",   "B Minor": "3m",   "F# Minor": "4m",
    "C# Minor": "5m",  "G# Minor": "6m",  "D# Minor": "7m",  "A# Minor": "8m",
    "F Minor": "9m",   "C Minor": "10m",  "G Minor": "11m",  "D Minor": "12m",
}


def obter_camelot(tom: str) -> str | None:
    """Retorna o código Camelot para uma tonalidade."""
    return TOM_PARA_CAMELOT.get(tom)


def obter_openkey(tom: str) -> str | None:
    """Retorna o código Open Key para uma tonalidade."""
    return TOM_PARA_OPENKEY.get(tom)


def _distancia_circular(a: int, b: int, modulo: int = 12) -> int:
    """Distância mínima entre dois números em anel circular."""
    diff = abs(a - b)
    return min(diff, modulo - diff)


def compatibilidade(tom_a: str, tom_b: str) -> dict:
    """
    Verifica compatibilidade harmônica entre duas tonalidades.

    Retorna um dicionário com:
    - nivel: 'perfeita' | 'boa' | 'arriscada' | 'incompativel'
    - descricao: explicação textual
    - camelot_a / camelot_b: códigos Camelot
    - distancia: distância na roda (0-6)
    """
    cam_a = TOM_PARA_CAMELOT.get(tom_a)
    cam_b = TOM_PARA_CAMELOT.get(tom_b)

    if cam_a is None or cam_b is None:
        return {
            "nivel": "desconhecida",
            "descricao": f"Tonalidade não reconhecida: {tom_a if cam_a is None else tom_b}",
            "camelot_a": cam_a,
            "camelot_b": cam_b,
            "distancia": -1,
        }

    num_a, letra_a = int(cam_a[:-1]), cam_a[-1]
    num_b, letra_b = int(cam_b[:-1]), cam_b[-1]
    dist = _distancia_circular(num_a, num_b)

    # Mesma posição exata
    if cam_a == cam_b:
        nivel, desc = "perfeita", "Mesma tonalidade"
    # Mesmo número, letra diferente (relativa maior/menor)
    elif num_a == num_b and letra_a != letra_b:
        nivel, desc = "perfeita", "Relativa maior/menor"
    # Vizinhas na roda (±1, mesma letra)
    elif dist == 1 and letra_a == letra_b:
        nivel, desc = "boa", "Vizinha na roda Camelot (±1)"
    # Vizinhas cruzadas (±1, letra diferente)
    elif dist == 1 and letra_a != letra_b:
        nivel, desc = "boa", "Vizinha cruzada na roda Camelot"
    # Distância 2 — pode funcionar
    elif dist == 2:
        nivel, desc = "arriscada", "Distância 2 — funciona com cuidado"
    # Salto de 7 semitons (boost de energia, técnica avançada)
    elif dist == 7:
        nivel, desc = "arriscada", "Salto de energia (+7) — técnica avançada"
    else:
        nivel, desc = "incompativel", f"Distância harmônica grande ({dist})"

    return {
        "nivel": nivel,
        "descricao": desc,
        "camelot_a": cam_a,
        "camelot_b": cam_b,
        "distancia": dist,
    }


def sugerir_proximas(tom: str) -> list[dict]:
    """
    Sugere tonalidades compatíveis para transição harmônica.

    Retorna lista ordenada por compatibilidade (perfeita → boa).
    """
    cam = TOM_PARA_CAMELOT.get(tom)
    if cam is None:
        return []

    num, letra = int(cam[:-1]), cam[-1]
    outra_letra = "A" if letra == "B" else "B"

    sugestoes = []

    # 1. Mesmo Camelot, mesma letra (mesma tonalidade — não faz sentido listar)
    # 2. Mesmo número, letra diferente (relativa)
    cod_rel = f"{num}{outra_letra}"
    if cod_rel in CAMELOT_PARA_TOM:
        sugestoes.append({
            "tom": CAMELOT_PARA_TOM[cod_rel],
            "camelot": cod_rel,
            "nivel": "perfeita",
            "descricao": "Relativa maior/menor",
        })

    # 3. Vizinhas (±1, mesma letra)
    for delta in [-1, 1]:
        viz_num = ((num - 1 + delta) % 12) + 1
        cod_viz = f"{viz_num}{letra}"
        if cod_viz in CAMELOT_PARA_TOM:
            sugestoes.append({
                "tom": CAMELOT_PARA_TOM[cod_viz],
                "camelot": cod_viz,
                "nivel": "boa",
                "descricao": f"Vizinha {'acima' if delta == 1 else 'abaixo'}",
            })

    # 4. Vizinhas cruzadas (±1, letra diferente)
    for delta in [-1, 1]:
        viz_num = ((num - 1 + delta) % 12) + 1
        cod_viz = f"{viz_num}{outra_letra}"
        if cod_viz in CAMELOT_PARA_TOM:
            sugestoes.append({
                "tom": CAMELOT_PARA_TOM[cod_viz],
                "camelot": cod_viz,
                "nivel": "boa",
                "descricao": f"Vizinha cruzada {'acima' if delta == 1 else 'abaixo'}",
            })

    return sugestoes
