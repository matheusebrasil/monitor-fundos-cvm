-- severidade: erro
-- A captação líquida do mart por classificação tem que bater com a soma do fato (diferença < R$ 1).
SELECT f.competencia, f.total_fato, m.total_mart
FROM (SELECT competencia, SUM(captacao_liquida) AS total_fato FROM fato_diario GROUP BY competencia) f
JOIN (SELECT competencia, SUM(captacao_liquida) AS total_mart FROM mart_captacao_classificacao GROUP BY competencia) m
  USING (competencia)
WHERE ABS(f.total_fato - m.total_mart) >= 1;
