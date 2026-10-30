-- Dimensão de classes de cotas: uma linha por CNPJ, com gestora e administrador do fundo.
--
-- Regras:
-- 1. Quando a CVM tem mais de um registro para o mesmo CNPJ de classe, fica o que está em
--    funcionamento e, entre eles, o de registro mais recente.
-- 2. Fundo em cogestão aparece em várias linhas do registro_fundo (uma por gestora): as
--    gestoras viram um rótulo só ("A / B") para a classe não ser contada duas vezes no ranking.
-- 3. Fundos que reportam o informe com o próprio CNPJ e não têm linha no cadastro de classes
--    (classe única / ainda não adaptados à Resolução CVM 175) entram pelo cadastro de fundos.
--    Sem isso, ~2,8% das classes do informe ficavam sem gestora.
-- 4. `investe_em_cotas` = 1 para fundo de fundos (FIC). O patrimônio dele já está dentro dos
--    fundos investidos: somar os dois conta o mesmo dinheiro duas vezes.

DROP VIEW IF EXISTS temp.v_fundo_unico;
CREATE TEMP VIEW v_fundo_unico AS
WITH gestoras AS (
    -- agregação única (a versão com subconsulta correlacionada ficava quadrática em 90 mil linhas)
    SELECT id_registro_fundo, GROUP_CONCAT(gestor, ' / ') AS gestor
    FROM (SELECT DISTINCT id_registro_fundo, gestor FROM stg_fundo
          WHERE gestor IS NOT NULL AND gestor <> ''
          ORDER BY id_registro_fundo, gestor)
    GROUP BY id_registro_fundo
)
SELECT f.id_registro_fundo, g.gestor, MAX(f.administrador) AS administrador
FROM stg_fundo f
LEFT JOIN gestoras g ON g.id_registro_fundo = f.id_registro_fundo
GROUP BY f.id_registro_fundo, g.gestor;

DROP TABLE IF EXISTS dim_classe;
CREATE TABLE dim_classe AS
WITH ordenado AS (
    SELECT c.*,
           ROW_NUMBER() OVER (
               PARTITION BY c.cnpj_classe
               ORDER BY CASE WHEN c.situacao = 'Em Funcionamento Normal' THEN 0 ELSE 1 END,
                        c.data_registro DESC
           ) AS rn
    FROM stg_classe c
)
SELECT o.cnpj_classe,
       o.denominacao_social                                     AS nome_classe,
       REPLACE(o.tipo_classe, 'Classes de Cotas de Fundos ', '') AS tipo_classe,
       COALESCE(NULLIF(o.classificacao, ''), 'Não informada')   AS classificacao,
       o.situacao,
       o.publico_alvo,
       o.exclusivo,
       COALESCE(NULLIF(f.gestor, ''), 'Não informado')        AS gestor,
       COALESCE(NULLIF(f.administrador, ''), 'Não informado') AS administrador,
       CASE WHEN o.classe_cotas = 'S' THEN 1 ELSE 0 END        AS investe_em_cotas,
       'cadastro de classes'                                  AS origem_cadastro
FROM ordenado o
LEFT JOIN v_fundo_unico f ON f.id_registro_fundo = o.id_registro_fundo
WHERE o.rn = 1;

INSERT INTO dim_classe
WITH fundo_ordenado AS (
    SELECT f.*, ROW_NUMBER() OVER (
               PARTITION BY f.cnpj_fundo
               ORDER BY CASE WHEN f.situacao = 'Em Funcionamento Normal' THEN 0 ELSE 1 END,
                        f.data_registro DESC) AS rn
    FROM stg_fundo f
)
SELECT o.cnpj_fundo, o.denominacao_social, o.tipo_fundo, 'Não informada', o.situacao, NULL, NULL,
       COALESCE(NULLIF(u.gestor, ''), 'Não informado'),
       COALESCE(NULLIF(u.administrador, ''), 'Não informado'),
       CASE WHEN o.tipo_fundo IN ('FACFIF', 'FICFIF') OR o.denominacao_social LIKE '%COTAS%' THEN 1 ELSE 0 END,
       'cadastro de fundos'
FROM fundo_ordenado o
LEFT JOIN v_fundo_unico u ON u.id_registro_fundo = o.id_registro_fundo
WHERE o.rn = 1
  AND o.cnpj_fundo NOT IN (SELECT cnpj_classe FROM dim_classe);

CREATE UNIQUE INDEX ix_dim_classe ON dim_classe (cnpj_classe);
