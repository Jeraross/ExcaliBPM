"""
Testes para music_analyzer.models — dataclass AnaliseMusical.
"""

import pytest

from music_analyzer.models import AnaliseMusical


class TestAnaliseMusicalStr:
    def test_str_contem_nome_arquivo(self, analise_exemplo):
        s = str(analise_exemplo)
        assert "track.wav" in s

    def test_str_contem_bpm(self, analise_exemplo):
        s = str(analise_exemplo)
        assert "128" in s

    def test_str_contem_tonalidade_geral(self, analise_exemplo):
        s = str(analise_exemplo)
        assert "C Major" in s

    def test_str_contem_codigos_camelot(self, analise_exemplo):
        s = str(analise_exemplo)
        assert "8B" in s   # C Major → 8B

    def test_str_sem_arquivo_nao_tem_linha_vazia_inicial(self):
        analise = AnaliseMusical(
            tonalidade_geral="A Minor",
            confianca_geral=0.9,
            tonalidade_inicio="A Minor",
            confianca_inicio=0.8,
            tonalidade_final="A Minor",
            confianca_final=0.8,
            bpm=120.0,
            duracao_segundos=60.0,
            arquivo="",
        )
        s = str(analise)
        # Linhas vazias originadas do arquivo vazio devem ser omitidas
        for linha in s.splitlines():
            assert linha.strip() != ""

    def test_str_duracao_formatada_em_minutos_segundos(self, analise_exemplo):
        # 212.5 s = 3 min 32 s
        s = str(analise_exemplo)
        assert "3:32" in s


class TestAnaliseMusicalToDict:
    def test_chaves_obrigatorias_presentes(self, analise_exemplo):
        d = analise_exemplo.to_dict()
        chaves_esperadas = {
            "arquivo", "duracao_segundos", "bpm",
            "tonalidade_geral", "camelot", "openkey", "confianca_geral",
            "tonalidade_inicio", "camelot_inicio", "confianca_inicio",
            "tonalidade_final", "camelot_final", "confianca_final",
        }
        assert chaves_esperadas.issubset(d.keys())

    def test_bpm_valor_correto(self, analise_exemplo):
        d = analise_exemplo.to_dict()
        assert d["bpm"] == 128.0

    def test_camelot_correto(self, analise_exemplo):
        d = analise_exemplo.to_dict()
        assert d["camelot"] == "8B"    # C Major
        assert d["camelot_final"] == "9B"   # G Major

    def test_openkey_correto(self, analise_exemplo):
        d = analise_exemplo.to_dict()
        assert d["openkey"] == "1d"    # C Major

    def test_confianca_arredondada_a_4_casas(self, analise_exemplo):
        d = analise_exemplo.to_dict()
        # Verifica que não há mais de 4 casas decimais
        confianca_str = str(d["confianca_geral"])
        partes = confianca_str.split(".")
        if len(partes) == 2:
            assert len(partes[1]) <= 4

    def test_duracao_arredondada_a_2_casas(self, analise_exemplo):
        d = analise_exemplo.to_dict()
        partes = str(d["duracao_segundos"]).split(".")
        if len(partes) == 2:
            assert len(partes[1]) <= 2


class TestAnaliseMusicalPropriedades:
    def test_camelot_property(self, analise_exemplo):
        assert analise_exemplo.camelot == "8B"

    def test_openkey_property(self, analise_exemplo):
        assert analise_exemplo.openkey == "1d"

    def test_camelot_inicio_property(self, analise_exemplo):
        assert analise_exemplo.camelot_inicio == "8B"

    def test_camelot_final_property(self, analise_exemplo):
        assert analise_exemplo.camelot_final == "9B"

    def test_camelot_tonalidade_desconhecida_retorna_interrogacao(self):
        analise = AnaliseMusical(
            tonalidade_geral="X Inválido",
            confianca_geral=0.0,
            tonalidade_inicio="X Inválido",
            confianca_inicio=0.0,
            tonalidade_final="X Inválido",
            confianca_final=0.0,
            bpm=0.0,
            duracao_segundos=0.0,
        )
        assert analise.camelot == "?"
        assert analise.openkey == "?"
