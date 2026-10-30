// Gera o código SDK do fluxo "Monitor de Fundos CVM — relatório" em n8n/dist/fluxo.ts,
// trocando __CHAVE__ pela chave de segredos.json (que não vai para o git). O e-mail de destino também vem de lá.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';

const aqui = (f) => new URL(f, import.meta.url);
const segredos = JSON.parse(readFileSync(aqui('../segredos.json'), 'utf8'));
if (!segredos.email_destino) throw new Error('segredos.json sem email_destino (veja segredos.exemplo.json)');
const caminho = new URL(segredos.n8n_webhook_url).pathname.replace(/^\/webhook\//, '');
const js = readFileSync(aqui('./montar_email.js'), 'utf8').replace('__CHAVE__', segredos.n8n_chave);

const TABELA = '80Pzcl44cuan2H4V'; // monitor_fundos_execucoes
const CRED_GMAIL = "{ id: 'w1UNnu6i7WZnfHSs', name: 'Gmail account' }";
const COLUNAS = [
  ['status', 'string'], ['competencia', 'string'], ['captacao_liquida_bi', 'number'], ['pl_fim_bi', 'number'],
  ['classes', 'number'], ['testes_ok', 'number'], ['testes_total', 'number'], ['arquivos_novos', 'number'],
  ['segundos', 'number'], ['origem_resumo', 'string'], ['recebido_em', 'dateTime'],
];
const valores = COLUNAS.map(([c]) => `${c}: expr('{{ $json.${c} }}')`).join(', ');
const esquema = COLUNAS.map(([c, t]) =>
  `{ id: '${c}', displayName: '${c}', required: false, defaultMatch: false, display: true, type: '${t}', canBeUsedToMatch: true }`).join(',\n        ');

const fluxo = `import { workflow, node, trigger, sticky, expr } from '@n8n/workflow-sdk';

const recebe = trigger({
  type: 'n8n-nodes-base.webhook', version: 2.1,
  config: { name: 'Pipeline Python terminou', parameters: { httpMethod: 'POST', path: ${JSON.stringify(caminho)}, responseMode: 'responseNode', options: {} }, position: [0, 300] },
  output: [{ body: { chave: 'x', status: 'ok', fatos: {}, testes: [], resumo: { frases: [], origem: 'ia' }, segundos: 90, arquivos_novos: 0 } }]
});

const montar = node({
  type: 'n8n-nodes-base.code', version: 2,
  config: { name: 'Conferir e montar e-mail', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: ${JSON.stringify(js)} }, position: [240, 300] },
  output: [{ assunto: 'Monitor', html: '<p>ok</p>', status: 'ok', competencia: '08/2026' }]
});

const enviar = node({
  type: 'n8n-nodes-base.gmail', version: 2.2,
  config: {
    name: 'Enviar relatório',
    parameters: { resource: 'message', operation: 'send', sendTo: ${JSON.stringify(segredos.email_destino)}, subject: expr('{{ $json.assunto }}'), emailType: 'html', message: expr('{{ $json.html }}'), options: { appendAttribution: false, senderName: 'Monitor de Fundos' } },
    credentials: { gmailOAuth2: ${CRED_GMAIL} },
    position: [480, 300]
  },
  output: [{ id: 'abc' }]
});

const historico = node({
  type: 'n8n-nodes-base.dataTable', version: 1.1,
  config: {
    name: 'Guardar no histórico',
    parameters: {
      resource: 'row', operation: 'insert',
      dataTableId: { __rl: true, mode: 'id', value: '${TABELA}' },
      columns: { mappingMode: 'defineBelow', value: { ${valores.replaceAll('$json.', '$("Conferir e montar e-mail").first().json.')} }, schema: [
        ${esquema}
      ] }
    },
    position: [720, 300]
  },
  output: [{ id: 1 }]
});

const responder = node({
  type: 'n8n-nodes-base.respondToWebhook', version: 1.5,
  config: { name: 'Responder ao Python', parameters: { respondWith: 'json', responseBody: expr('{{ JSON.stringify({ ok: true, status: $("Conferir e montar e-mail").first().json.status, historico_id: $json.id }) }}'), options: {} }, position: [960, 300] },
  output: [{ ok: true }]
});

const nota = sticky('## Monitor de Fundos CVM\\nO pipeline em **Python** roda no PC (extrai 2 mi de linhas da CVM, transforma em SQL, testa a qualidade) e manda o resultado para cá.\\n\\nO **n8n** confere a chave, monta o e-mail, guarda o histórico da execução e responde ao Python.', [recebe, montar, enviar, historico, responder], { color: 5 });

export default workflow('monitor-fundos-cvm', 'Monitor de Fundos CVM — relatório', { executionOrder: 'v1', timezone: 'America/Sao_Paulo', errorWorkflow: 'sEd8QAcZyDVz16XT' })
  .add(recebe).to(montar).to(enviar).to(historico).to(responder)
  .add(nota);
`;

mkdirSync(aqui('./dist/'), { recursive: true });
writeFileSync(aqui('./dist/fluxo.ts'), fluxo);
console.log('dist/fluxo.ts gerado,', fluxo.length, 'caracteres');
