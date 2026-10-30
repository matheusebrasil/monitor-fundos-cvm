-- severidade: aviso
-- limite: 0.02
-- base: SELECT COUNT(DISTINCT cnpj_classe) FROM fato_diario
-- Classes do informe sem cadastro na CVM. Tolerado até 2% (classe recém-registrada).
SELECT DISTINCT f.cnpj_classe FROM fato_diario f
LEFT JOIN dim_classe d USING (cnpj_classe) WHERE d.cnpj_classe IS NULL;
