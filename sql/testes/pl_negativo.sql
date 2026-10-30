-- severidade: aviso
-- Classes com patrimônio negativo em algum dia (passivo maior que o ativo — em geral fundo em
-- dificuldade ou em liquidação). É dado real, não erro de carga: fica como aviso, por classe.
SELECT cnpj_classe, COUNT(*) AS dias_negativos, MIN(pl) AS pior_pl
FROM fato_diario WHERE pl < 0 GROUP BY cnpj_classe;
