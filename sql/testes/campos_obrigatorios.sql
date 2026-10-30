-- severidade: erro
-- CNPJ, data e cota não podem faltar.
SELECT * FROM fato_diario WHERE cnpj_classe IS NULL OR cnpj_classe = '' OR data IS NULL OR vl_quota IS NULL;
