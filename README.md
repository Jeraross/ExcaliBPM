# Music Analyzer

Detecção robusta de **tonalidade** e **BPM** para aplicações de mixagem de músicas.

## Técnicas implementadas

| Técnica | Motivo |
|---------|--------|
| HPSS com `margin=8` | Isola harmônicos, remove percussão que polui o cromagrama |
| Chroma CQT (`bins_per_octave=36`) | 3 bins/semitom → melhor separação tônica vs dominante |
| Correção automática de afinação | Evita vazamento cromático em gravações desafinadas |
| Filtragem non-local + mediana | Remove ruído espectral, suaviza sem perder transições |
| Ponderação por energia (RMS) | Refrões pesam mais que intros silenciosas |
| 8 perfis de tonalidade (ensemble) | Votação entre Krumhansl, Temperley, Bellman-Budge, Aarden, etc. |
| Votação frame-a-frame (~4s) | Robusto contra modulações e bridges |
| Análise de registro grave | Desambigua tônica em casos como C Major vs A Minor |
| Análise de endpoints | Início e fim da música reforçam identificação da tônica |
| Meta-ensemble CQT + CENS | Dois tipos de chroma votam juntos |

## Estrutura do projeto

```
music_analyzer/
├── main.py                          # CLI
├── requirements.txt
├── README.md
└── music_analyzer/                  # Pacote Python
    ├── __init__.py                  # API pública
    ├── core.py                      # Orquestrador principal
    ├── chroma.py                    # Extração de cromagrama
    ├── key_detect.py                # Algoritmos de detecção de tom
    ├── bpm.py                       # Detecção de BPM
    ├── camelot.py                   # Roda Camelot + compatibilidade
    ├── models.py                    # Dataclasses de resultado
    └── profiles.py                  # 8 conjuntos de perfis de tonalidade
```

## Instalação

```bash
pip install -r requirements.txt
```

## Uso via CLI

```bash
# Análise básica
python main.py musica.wav

# Múltiplos arquivos em JSON
python main.py *.mp3 --json

# Verificar compatibilidade entre duas faixas
python main.py track_a.wav --compativel-com track_b.wav

# Mostrar sugestões de tons para próxima faixa
python main.py track.wav --sugestoes

# Debug: ver votos de cada perfil e frame
python main.py track.wav --debug
```

## Uso como biblioteca

```python
from music_analyzer import analisar_musica, compatibilidade, sugerir_proximas

# Análise completa
resultado = analisar_musica("track.wav")
print(resultado)
print(resultado.to_dict())    # Para JSON/API

# Compatibilidade para transição
faixa_a = analisar_musica("track_a.wav")
faixa_b = analisar_musica("track_b.wav")

compat = compatibilidade(faixa_a.tonalidade_final, faixa_b.tonalidade_inicio)
print(compat)
# {'nivel': 'boa', 'descricao': 'Vizinha na roda Camelot (+1)', ...}

# Sugestões de próximas faixas
sugestoes = sugerir_proximas(faixa_a.tonalidade_geral)
for s in sugestoes:
    print(f"{s['camelot']} {s['tom']} — {s['nivel']}")
```

## Saída exemplo

```
════════════════════════════════════════════════════════
  ANÁLISE MUSICAL
  theSpins.wav
════════════════════════════════════════════════════════
  Duração        : 3:15
  BPM            : 126.0
────────────────────────────────────────────────────────
  Tom Geral      : A Minor        │ 8A   │ 75%
  Tom Início     : A Minor        │ 8A   │ 62%
  Tom Final      : A Minor        │ 8A   │ 68%
════════════════════════════════════════════════════════
```

## Integração com aplicação de mixagem

O método `to_dict()` retorna um dicionário pronto para JSON, ideal para APIs:

```python
import json
resultado = analisar_musica("track.wav")
json.dumps(resultado.to_dict())
```

```json
{
  "arquivo": "track.wav",
  "bpm": 126.0,
  "tonalidade_geral": "A Minor",
  "camelot": "8A",
  "openkey": "1m",
  "confianca_geral": 0.75,
  "tonalidade_inicio": "A Minor",
  "tonalidade_final": "A Minor",
  ...
}
```

Para verificar se duas faixas mixam bem, compare o **tom final** da faixa que está saindo
com o **tom de início** da faixa que está entrando:

```python
compat = compatibilidade(faixa_saindo.tonalidade_final, faixa_entrando.tonalidade_inicio)
if compat["nivel"] in ("perfeita", "boa"):
    print("Transição harmônica segura!")
```
