-- Fato diário no nível da classe.
-- 1. As linhas de subclasse (≈1% do arquivo) ficam fora para não contar o mesmo patrimônio duas vezes.
-- 2. O arquivo da CVM às vezes repete a MESMA linha inteira (todos os campos iguais): o DISTINCT
--    remove só essa cópia exata. Duas linhas do mesmo dia com valores DIFERENTES continuam aqui
--    e fazem o teste `unicidade_fato` falhar — conflito de verdade precisa de olho humano.
DROP TABLE IF EXISTS fato_diario;
CREATE TABLE fato_diario AS
SELECT DISTINCT
       competencia,
       cnpj_classe,
       DATE(data)                      AS data,
       vl_quota,
       pl,
       COALESCE(captacao, 0)           AS captacao,
       COALESCE(resgate, 0)            AS resgate,
       COALESCE(captacao, 0) - COALESCE(resgate, 0) AS captacao_liquida,
       cotistas
FROM stg_informe
WHERE id_subclasse IS NULL OR id_subclasse = '';
CREATE INDEX ix_fato_classe_data ON fato_diario (cnpj_classe, data);
CREATE INDEX ix_fato_comp ON fato_diario (competencia);
