-- severidade: erro
-- Número de cotistas, captação e resgate nunca são negativos.
SELECT * FROM fato_diario WHERE cotistas < 0 OR captacao < 0 OR resgate < 0;
