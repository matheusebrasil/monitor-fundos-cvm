-- Uma linha por classe e mês: fluxo do mês, PL no último dia informado e rentabilidade da cota.
DROP TABLE IF EXISTS mart_classe_mes;
CREATE TABLE mart_classe_mes AS
WITH limites AS (
    SELECT competencia, cnpj_classe, MIN(data) AS primeiro_dia, MAX(data) AS ultimo_dia,
           SUM(captacao) AS captacao, SUM(resgate) AS resgate, SUM(captacao_liquida) AS captacao_liquida
    FROM fato_diario
    GROUP BY competencia, cnpj_classe
)
SELECT l.competencia, l.cnpj_classe, l.captacao, l.resgate, l.captacao_liquida,
       fim.pl        AS pl_fim,
       fim.cotistas  AS cotistas_fim,
       CASE WHEN ini.vl_quota > 0 THEN fim.vl_quota / ini.vl_quota - 1 END AS rent_mes
FROM limites l
JOIN fato_diario ini ON ini.cnpj_classe = l.cnpj_classe AND ini.data = l.primeiro_dia
JOIN fato_diario fim ON fim.cnpj_classe = l.cnpj_classe AND fim.data = l.ultimo_dia;
CREATE INDEX ix_mcm ON mart_classe_mes (competencia, cnpj_classe);
