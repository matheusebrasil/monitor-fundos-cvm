import argparse

import pytest

import executar


@pytest.mark.parametrize(("valor", "esperado"), [("1", 1), ("4", 4)])
def test_meses_positivos_sao_aceitos(valor, esperado):
    assert executar.meses_positivo(valor) == esperado


@pytest.mark.parametrize("valor", ["0", "-1", "-3", "abc"])
def test_meses_invalidos_sao_recusados(valor):
    with pytest.raises(argparse.ArgumentTypeError, match="inteiro maior ou igual a 1"):
        executar.meses_positivo(valor)


# A função acima sozinha não basta: o que protege o banco é o parser de verdade usá-la.
# Só lê os argumentos (nada de executar()), então é seguro mesmo se a ligação estiver errada.
@pytest.mark.parametrize("valor", ["0", "-3", "abc"])
def test_parser_recusa_meses_invalidos_com_codigo_2(valor, capsys):
    with pytest.raises(SystemExit) as saida:
        executar.montar_parser().parse_args(["--meses", valor])
    assert saida.value.code == 2
    assert "inteiro maior ou igual a 1" in capsys.readouterr().err


def test_parser_usa_a_janela_padrao_sem_meses():
    assert executar.montar_parser().parse_args([]).meses == executar.config.MESES_PADRAO
