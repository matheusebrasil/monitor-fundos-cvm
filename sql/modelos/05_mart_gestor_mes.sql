-- Ranking de gestoras: captação líquida do mês e posição no ranking (window function).
DROP TABLE IF EXISTS mart_gestor_mes;
CREATE TABLE mart_gestor_mes AS
WITH base AS (
    SELECT m.competencia, COALESCE(d.gestor, 'Sem cadastro') AS gestor,
           COUNT(*) AS classes, SUM(m.captacao_liquida) AS captacao_liquida, SUM(m.pl_fim) AS pl_fim
    FROM mart_classe_mes m
    LEFT JOIN dim_classe d USING (cnpj_classe)
    GROUP BY m.competencia, COALESCE(d.gestor, 'Sem cadastro')
)
SELECT *,
       RANK() OVER (PARTITION BY competencia ORDER BY captacao_liquida DESC) AS posicao_captacao,
       RANK() OVER (PARTITION BY competencia ORDER BY pl_fim DESC)           AS posicao_pl
FROM base;
