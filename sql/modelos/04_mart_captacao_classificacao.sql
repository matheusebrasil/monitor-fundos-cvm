-- Visão de mercado: captação líquida e patrimônio por classificação CVM, mês a mês.
-- pl_fim soma tudo (bruto); pl_fim_consolidado tira os fundos de fundos para não contar duas vezes.
DROP TABLE IF EXISTS mart_captacao_classificacao;
CREATE TABLE mart_captacao_classificacao AS
SELECT m.competencia,
       COALESCE(d.classificacao, 'Sem cadastro') AS classificacao,
       COUNT(*)                   AS classes,
       SUM(m.captacao)            AS captacao,
       SUM(m.resgate)             AS resgate,
       SUM(m.captacao_liquida)    AS captacao_liquida,
       SUM(m.pl_fim)              AS pl_fim,
       SUM(CASE WHEN COALESCE(d.investe_em_cotas, 0) = 0 THEN m.pl_fim ELSE 0 END) AS pl_fim_consolidado,
       SUM(m.cotistas_fim)        AS cotistas_fim
FROM mart_classe_mes m
LEFT JOIN dim_classe d USING (cnpj_classe)
GROUP BY m.competencia, COALESCE(d.classificacao, 'Sem cadastro');
