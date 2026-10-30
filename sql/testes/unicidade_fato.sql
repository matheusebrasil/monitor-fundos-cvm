-- severidade: erro
-- Cada classe só pode ter uma linha por dia no fato.
SELECT cnpj_classe, data, COUNT(*) AS repeticoes
FROM fato_diario GROUP BY cnpj_classe, data HAVING COUNT(*) > 1;
