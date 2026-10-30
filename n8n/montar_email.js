// Nó "Conferir e montar e-mail" do fluxo "Monitor de Fundos CVM — relatório".
// Recebe o POST do pipeline em Python, confere a chave e monta o e-mail
// (relatório quando o pipeline passou; alerta quando a qualidade barrou).

const CHAVE = '__CHAVE__';

const corpo = $input.first().json.body || {};
if (String(corpo.chave || '') !== CHAVE) {
  throw new Error('Chave do monitor inválida.');
}

const fatos = corpo.fatos || {};
const mes = fatos.mes_atual || {};
const testes = Array.isArray(corpo.testes) ? corpo.testes : [];
const resumo = corpo.resumo || { frases: [], origem: '' };
const bloqueado = corpo.status !== 'ok';
const passaram = testes.filter((t) => t.passou).length;

const num = (n, casas = 1) =>
  typeof n === 'number'
    ? n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })
    : '—';
const sinal = (n) => (typeof n === 'number' && n > 0 ? '+' : '') + num(n);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

const COR = { tinta: '#1f2933', suave: '#52606d', linha: '#e4e7eb', fundo: '#f5f7fa',
  verde: '#2f855a', vermelho: '#c53030', ambar: '#b7791f', azul: '#2b6cb0' };
const corValor = (n) => (n > 0 ? COR.verde : n < 0 ? COR.vermelho : COR.tinta);

const cartao = (rotulo, valor, cor = COR.tinta) => `
  <td style="padding:14px 16px;background:${COR.fundo};border-radius:8px;width:33%">
    <div style="font-size:12px;color:${COR.suave};text-transform:uppercase;letter-spacing:.04em">${rotulo}</div>
    <div style="font-size:22px;font-weight:700;color:${cor};margin-top:4px">${valor}</div>
  </td>`;

const linhasClassificacao = (fatos.por_classificacao || []).map((c) => `
  <tr>
    <td style="padding:6px 0;border-bottom:1px solid ${COR.linha}">${esc(c.nome)}</td>
    <td style="padding:6px 0;border-bottom:1px solid ${COR.linha};text-align:right;color:${corValor(c.captacao_liquida_bi)}">${sinal(c.captacao_liquida_bi)}</td>
    <td style="padding:6px 0;border-bottom:1px solid ${COR.linha};text-align:right">${num(c.pl_fim_bi)}</td>
  </tr>`).join('');

const linhasGestoras = (fatos.top5_gestoras_captacao_bi || []).map((g, i) => `
  <tr>
    <td style="padding:6px 0;border-bottom:1px solid ${COR.linha}">${i + 1}. ${esc(g.gestora)}</td>
    <td style="padding:6px 0;border-bottom:1px solid ${COR.linha};text-align:right;color:${corValor(g.captacao_liquida_bi)}">${sinal(g.captacao_liquida_bi)}</td>
  </tr>`).join('');

const linhasTestes = testes.map((t) => {
  const cor = t.passou ? COR.verde : t.severidade === 'erro' ? COR.vermelho : COR.ambar;
  const marca = t.passou ? 'OK' : t.severidade === 'erro' ? 'BARROU' : 'AVISO';
  return `
  <tr>
    <td style="padding:5px 0;border-bottom:1px solid ${COR.linha};font-family:Consolas,monospace;font-size:13px">${esc(t.teste)}</td>
    <td style="padding:5px 0;border-bottom:1px solid ${COR.linha};text-align:right;color:${cor};font-weight:700;font-size:12px">${marca}</td>
    <td style="padding:5px 0 5px 12px;border-bottom:1px solid ${COR.linha};text-align:right;color:${COR.suave};font-size:13px">${t.violacoes} ${t.violacoes === 1 ? 'violação' : 'violações'}</td>
  </tr>`;
}).join('');

const secao = (titulo, conteudo) => `
  <h3 style="font-size:15px;margin:26px 0 8px;color:${COR.tinta}">${titulo}</h3>${conteudo}`;

const tabela = (cab, corpoTabela) => `
  <table style="width:100%;border-collapse:collapse;font-size:14px;color:${COR.tinta}">
    <tr style="color:${COR.suave};font-size:12px;text-transform:uppercase">${cab}</tr>${corpoTabela}
  </table>`;

const faixa = bloqueado
  ? `<div style="background:#fff5f5;border-left:4px solid ${COR.vermelho};padding:12px 14px;margin:18px 0;color:${COR.tinta}">
       <b>Relatório barrado pelo portão de qualidade.</b> Um teste com severidade "erro" falhou,
       então nenhum número foi publicado. Veja abaixo qual foi.</div>`
  : '';

const corpoRelatorio = bloqueado ? '' : `
  <table style="width:100%;border-collapse:separate;border-spacing:8px 0;margin:18px -8px 0"><tr>
    ${cartao('Captação líquida', 'R$ ' + sinal(mes.captacao_liquida_bi) + ' bi', corValor(mes.captacao_liquida_bi))}
    ${cartao('Patrimônio no fim do mês', 'R$ ' + num(mes.pl_fim_bi) + ' bi')}
    ${cartao('Classes de fundos', num(mes.classes, 0))}
  </tr></table>
  ${secao('Resumo do mês', '<ul style="margin:0;padding-left:18px;color:' + COR.tinta + ';font-size:14px;line-height:1.6">' +
    (resumo.frases || []).map((f) => '<li>' + esc(f) + '</li>').join('') + '</ul>')}
  ${secao('Captação por classificação (R$ bi)', tabela(
    '<td>Classificação</td><td style="text-align:right">Captação</td><td style="text-align:right">PL</td>', linhasClassificacao))}
  ${secao('Top 5 gestoras em captação (R$ bi)', tabela(
    '<td>Gestora</td><td style="text-align:right">Captação</td>', linhasGestoras))}`;

const rodape = `Pipeline em Python: ${num(corpo.segundos)} s · ${corpo.arquivos_novos ?? 0} arquivo(s) novo(s) na CVM · ` +
  `resumo: ${resumo.origem === 'ia' ? 'IA local (Ollama), com cada número conferido' : 'modelo fixo'} · orquestração: n8n`;

const html = `
<div style="font-family:Segoe UI,Arial,sans-serif;max-width:640px;margin:0 auto;padding:24px;color:${COR.tinta}">
  <div style="font-size:12px;color:${COR.azul};font-weight:700;letter-spacing:.06em">MONITOR DE FUNDOS · DADOS ABERTOS DA CVM</div>
  <h2 style="margin:6px 0 0;font-size:22px">Fundos de investimento — ${esc(mes.competencia || corpo.competencia || '')}</h2>
  ${faixa}
  ${corpoRelatorio}
  ${secao(`Qualidade dos dados: ${passaram} de ${testes.length} testes passaram`, tabela(
    '<td>Teste</td><td style="text-align:right">Resultado</td><td style="text-align:right">Linhas</td>', linhasTestes))}
  <p style="margin-top:26px;font-size:12px;color:${COR.suave}">${rodape}</p>
</div>`;

const competencia = mes.competencia || corpo.competencia || '';
return [{
  json: {
    assunto: bloqueado
      ? `Monitor de Fundos: relatório de ${competencia} barrado pela qualidade`
      : `Monitor de Fundos ${competencia}: captação de R$ ${sinal(mes.captacao_liquida_bi)} bi`,
    html,
    status: bloqueado ? 'bloqueado' : 'ok',
    competencia,
    captacao_liquida_bi: typeof mes.captacao_liquida_bi === 'number' ? mes.captacao_liquida_bi : null,
    pl_fim_bi: typeof mes.pl_fim_bi === 'number' ? mes.pl_fim_bi : null,
    classes: typeof mes.classes === 'number' ? mes.classes : null,
    testes_ok: passaram,
    testes_total: testes.length,
    arquivos_novos: Number(corpo.arquivos_novos || 0),
    segundos: Number(corpo.segundos || 0),
    origem_resumo: resumo.origem || '',
    recebido_em: new Date().toISOString(),
  },
}];
