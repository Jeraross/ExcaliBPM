#!/usr/bin/env python3
"""
CLI para análise musical.

Uso:
    python main.py track.wav
    python main.py track1.mp3 track2.flac --json
    python main.py track_a.wav --compativel-com track_b.wav
"""

import argparse
import json
import sys
import os

from music_analyzer import (
    analisar_musica,
    compatibilidade,
    sugerir_proximas,
)


def main():
    parser = argparse.ArgumentParser(
        description="Análise musical robusta — tonalidade, BPM e compatibilidade Camelot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py musica.wav
  python main.py *.mp3 --json
  python main.py track_a.wav --compativel-com track_b.wav
  python main.py track.wav --sugestoes
        """,
    )

    parser.add_argument(
        "arquivos",
        nargs="+",
        help="Arquivo(s) de áudio para analisar",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Saída em formato JSON",
    )
    parser.add_argument(
        "--compativel-com",
        metavar="ARQUIVO",
        help="Verifica compatibilidade harmônica com outro arquivo",
    )
    parser.add_argument(
        "--sugestoes",
        action="store_true",
        help="Mostra tons compatíveis para transição (Camelot)",
    )
    parser.add_argument(
        "--sr",
        type=int,
        default=22050,
        help="Taxa de amostragem (padrão: 22050)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mostra votos detalhados de cada perfil",
    )

    args = parser.parse_args()

    resultados = []

    for arquivo in args.arquivos:
        if not os.path.exists(arquivo):
            print(f"Arquivo não encontrado: {arquivo}", file=sys.stderr)
            continue

        print(f"\nAnalisando: {arquivo}...", file=sys.stderr)

        try:
            r = analisar_musica(arquivo, sr=args.sr)
            resultados.append(r)

            if args.json:
                continue

            print(r)

            if args.debug:
                print("\n  Votos por perfil:")
                for perfil, tom in r.votos_perfis.items():
                    print(f"    {perfil:<25} → {tom}")
                if r.votos_frames:
                    from collections import Counter
                    contagem = Counter(r.votos_frames)
                    print(f"\n  Votos por frame ({len(r.votos_frames)} segmentos):")
                    for tom, n in contagem.most_common(5):
                        barra = "█" * n
                        print(f"    {tom:<14} {barra} ({n})")

            if args.sugestoes:
                sug = sugerir_proximas(r.tonalidade_geral)
                print(f"\n  Tons compatíveis para transição a partir de {r.tonalidade_geral} ({r.camelot}):")
                for s in sug:
                    print(f"    {s['camelot']:<5} {s['tom']:<14} — {s['descricao']} [{s['nivel']}]")

        except Exception as e:
            print(f"Erro ao analisar {arquivo}: {e}", file=sys.stderr)

    # Compatibilidade entre duas faixas
    if args.compativel_com and resultados:
        print(f"\nAnalisando: {args.compativel_com}...", file=sys.stderr)
        try:
            r_b = analisar_musica(args.compativel_com, sr=args.sr)
            if not args.json:
                print(r_b)

            r_a = resultados[0]

            compat = compatibilidade(r_a.tonalidade_final, r_b.tonalidade_inicio)

            if args.json:
                resultados.append(r_b)
            else:
                print(f"\n{'─' * 56}")
                print("  COMPATIBILIDADE PARA TRANSIÇÃO")
                print(f"{'─' * 56}")
                print(f"  {r_a.arquivo}")
                print(f"    Tom final: {r_a.tonalidade_final} ({r_a.camelot_final})")
                print(f"  {r_b.arquivo}")
                print(f"    Tom início: {r_b.tonalidade_inicio} ({r_b.camelot_inicio})")
                print(f"{'─' * 56}")
                emoji = {"perfeita": "✓", "boa": "~", "arriscada": "!", "incompativel": "✗"}
                e = emoji.get(compat["nivel"], "?")
                print(f"  [{e}] {compat['nivel'].upper()} — {compat['descricao']}")
                print(f"  Distância Camelot: {compat['distancia']}")
                print(f"{'─' * 56}")

        except Exception as e:
            print(f"Erro ao analisar {args.compativel_com}: {e}", file=sys.stderr)

    # Saída JSON
    if args.json:
        dados = [r.to_dict() for r in resultados]
        print(json.dumps(dados, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
