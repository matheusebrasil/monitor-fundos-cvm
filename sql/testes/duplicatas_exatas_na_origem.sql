-- severidade: aviso
-- Linhas repetidas por inteiro no arquivo da CVM (removidas no fato pelo DISTINCT).
-- Fica como aviso para o relatório mostrar quanto a fonte veio suja.
SELECT competencia, cnpj_classe, data, COUNT(*) AS copias
FROM stg_informe
WHERE id_subclasse IS NULL OR id_subclasse = ''
GROUP BY competencia, cnpj_classe, data, vl_quota, pl, captacao, resgate, cotistas
HAVING COUNT(*) > 1;
