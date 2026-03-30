# Módulo de Conciliação Bancária Implementado

Conforme planejado, implementamos o **Caminho 2 (O Feitiço de Fusão)**.

## O Que Foi Forjado:

### 1. Algoritmo de Conciliação (`core/services.py`)
Quando você importa uma fatura, o Oráculo (Gemini) extrai os dados. Antes de salvar no banco, o sistema agora faz uma varredura:
- Ele busca por transações lançadas manualmente (`PENDENTE`) no mesmo cartão e com **exatamente o mesmo valor**.
- Ele aceita uma margem de **1 dia para mais ou para menos** na data da compra (pois as maquininhas de cartão frequentemente registram a compra perto da meia-noite no dia seguinte ou anterior dependendo do fuso).
- Se encontrar um "match", ele **funde** os dados: mantendo o nome amigável que você cadastrou (ex: "Pó de café") e apenas alterando o status para `FATURADO`, amarrando aquela despesa à fatura do mês atual.

### 2. Missão Diária: +5 XP (`core/views.py`)
Adicionamos o incentivo para que você continue lançando os gastos diários! Cada vez que usar o botão de "Registrar Despesa", você (o Titular) ganha **+5 XP**. O sistema também exibe alertas (Toast/Mensagens) informando sobre o ganho de XP e parabenizando caso você suba de nível (`LEVEL UP!`).

## Como Verificar o Feitiço:
1. Registre uma despesa avulsa normalmente no painel (ex: R$ 50,00 no dia de hoje com o título "Almoço").
2. Gere um PDF falso (ou real) que contenha uma transação de exatos R$ 50,00 no mesmo dia (pode ter o nome feio do restaurante como "RESTAURANTE DO JOSE LTDA").
3. Importe essa fatura.
4. Verifique que o sistema **não duplicou** a transação de R$ 50,00, mas pegou a sua manual "Almoço" e atualizou o status dela para Faturado! ⚔️

## Correção Recente: Destruir Loot (Exclusão)

### O Problema:
O botão de lixeira no Dashboard não funcionava e na tela de Pergaminhos (Extrato Completo) ele sequer existia.

### A Solução:
1. **Magia de Destruição (JS):** O feitiço `deletarTransacao` foi forjado no pergaminho mestre (`base.html`), o que significa que agora o botão funciona perfeitamente em todas as telas. Ele usa o token de segurança (`CSRFToken`) para despachar um sinal de `DELETE` para a nossa guilda (API).
2. **Nova Interface:** O botão com a Lixeira foi adicionado também na tela do Extrato Completo, alinhado junto ao botão de Dividir Despesa, mantendo a consistência visual. Elevamos também o aviso de confirmação ("Tem certeza que deseja destruir este loot?") para evitar o descarte acidental.
 - Integrated Django Admin link in the top navigation bar for quick access.
  - Split the "Banco da Guilda" forging buttons into two distinct actions with separate modals ("Forjar Instituição" and "Forjar Nova Meta") to streamline the user flow.

### Quartel-General UI Overhaul
- **Central de Cadastros Redesign**:
  - Removed the side-by-side 3-column layout that constrained the list view.
  - Form inputs for Renda, Pessoas, Cartões, and Categorias are now floating Modals (consistent with the "Forjar" feature).
  - The history and active lists now expand to 100% width, utilizing a fully responsive CSS Grid layout to prevent visual clutter as records grow.

### API Upgrades
- **Google GenAI Migration**:
  - Upgraded the `core.services` module from the legacy `google-generativeai` package to the newly recommended `google-genai` package.
  - Adapted the API call from `model.generate_content` to `client.models.generate_content` using the robust `gemini-2.5-flash` model structure.

### Fatura (Invoice) Generation Modal Refactor
- **Consolidated Dashboard Action**:
  - Removed the standalone "Mural de Cobranças" page and its corresponding top-level navigation link in order to clean up the UI.
  - Integrated the Invoice Generation form directly into the `Dashboard` via a newly added "Emitir Fatura" floating button (`bottom-40 right-8`).
  - The form is now presented inside a sleek, dark-themed Modal (`modal-fatura`) maintaining consistency with the "Oráculo" experience.

### Dynamic Auto-Split (Rateio) Modal Refactor
- **Consolidated Action & UX Engine**:
  - Removed the dedicated `ratear_transacao.html` page and simplified the backend view.
  - Clicking "Dividir Despesa" on any transaction (in Dashboard or Extrato) now opens a universal, floating `modal_rateio.html`.
  - Added a highly responsive JavaScript engine that automatically divides the total transaction value equally whenever a new Ally is brought into the split.
  - Users can still manually override individual fields (e.g. 50/10 split instead of 30/30). The form will only unlock the Submit button if the sum of all parts perfectly matches the expense's Total Value.
  - Submitting the rateio performs the backend split and dynamically redirects the user back to the exact screen they were on (`HTTP_REFERER`).

## Tests Performed
## Correção Recente: Redirecionamento da Forja (Oráculo)

### O Problema:
Quando você importava uma fatura, o sistema salvava tudo no banco de dados perfeitamente, mas "teletransportava" você para a tela de *Mural de Recompensas*. Ao voltar manualmente para o *Dashboard*, ele mostrava por padrão o **Mês Atual** (ex: Março). Se você tivesse importado uma fatura de **Fevereiro**, parecia que os dados não tinham sido salvos, pois eles estavam escondidos no mês anterior.

### A Solução:
O código do Oráculo (`views.py -> importar_fatura`) foi recalibrado. Agora, assim que a extração termina, o sistema teletransporta você automaticamente para a página de **Pergaminhos (Extrato Completo)** e já aplica os **Filtros Automáticos** (Mês, Ano e Cartão) exatos da fatura que você acabou de importar.
Dessa forma, os dados saltam aos olhos imediatamente!

## Correção Recente: Extração de Dados da IA
### O Problema:
Ao ler faturas, o Oráculo estava devolvendo o erro `Expecting value: line 1 column 1` caso a inteligência artificial (Gemini) falasse "Aqui está o seu JSON:" antes de enviar os dados corretos que havíamos pedido, quebrando a tradução de "texto para banco de dados".

### A Solução:
Ao invés de tentar ler o texto de cara, forjei um novo algoritmo "Caçador de Colchetes" no `services.py`. O sistema agora vasculha a resposta da IA atrás do bloco `[` e `]`, arrancando fora qualquer conversa paralela ou formatação Markdown e extraindo apenas o ouro (os dados reais da fatura). Isso vai deixar a extração à prova de falhas com falas inesperadas da IA!

## Nova Funcionalidade: Obliterar Fatura Inteira (Exclusão em Massa)
### O Recurso:
Para resolver a necessidade de "limpar o mês" caso o usuário tenha importado o PDF errado, foi criada a magia "Obliterar Fatura".
1. Vá até os **Pergaminhos (Extrato Completo)**.
2. Utilize os filtros superiores para selecionar o combo exato: `Mês` + `Ano` + `Arma (Cartão)`.
3. Ao clicar em **Filtrar Registros**, o amuleto de segurança cai e o botão **Obliterar Fatura** magicamente surge ao lado.
4. Clicar nele evoca um Modal de Confirmação Supremo. Confirmando, **todos** os registros pertencentes àquele cartão naquela competência são varridos de uma só vez do banco de dados, poupando a mão do herói ao invés de deletar de 1 em 1.

## Nova Funcionalidade: Visão da Party (Dashboard Cooperativo)
### O Recurso:
O cérebro do sistema (`views.py`) foi atualizado para processar silenciosamente a soma de moedas gastas por cada integrante da equipe (Responsável) dentro do mês que está sendo exibido na tela inicial.
1. Na **Visão Geral** (Dashboard), foram inseridas duas abas (Tabs) no topo: `Visão Pessoal` e `Visão da Party`.
2. O sistema funciona como uma ponte levadiça: clicar em uma esconde a outra instantaneamente através de Javascript (`mudarAbaDashboard`).
3. Na `Visão da Party`, você encontrará um mostruário moderno em forma de Cards. Cada Card exibe a foto do perfil do guerreiro (ou a inicial do nome), sua classe atual de RPG, nível e o total gasto no mês filtrado.
4. Se existirem gastos importados ou criados sem nenhum dono atribuído, um card especial chamado `Loot Sem Dono` aparecerá no final para avisar qual a fatia do tesouro que não tem nenhum pai.

## Evolução de Sistema: Combate de Boss Melhorado
### O Recurso:
Foi reescrita toda a lógica de "Enfrentar Boss do Mês" para tapar algumas brechas ("exploits") de farm de XP infinito:
1. **Sincronia Temporal:** O botão "Iniciar Combate" agora afeta apenas o Mês e Ano que estiverem filtrados no seu relógio superior do Dashboard (ao invés de puxar sempre o mês local do seu computador).
2. **Bloqueio de Mapa Vazio:** Não é mais possível fechar um mês sem faturas (zerado) para se testar. O Boss simplesmente não aparece, emitindo um aviso amigável que não há loot ou inimigos no mapa.
3. **Memória de Longo Prazo:** Foi criado um cofre no banco de dados (`meses_fechados`) que armazena todo o histórico dos meses derrotados.
4. **Anti-Exploit:** Se você deletar faturas antigas e jogar os dados do zero, você **pode enfrentar** o Boss de novo para atualizar seus cálculos/telas, mas o sistema vai puxar da memória e avisar que o XP já foi coletado e não irá creditar mais moedas/experiência repetida.

## Polimento e Responsividade Mobile 📱
### O Recurso:
O sistema agora está 100% pronto para ser usado como um Web App no seu celular! Realizamos um pente fino nas telas principais para ajustar a usabilidade em telas pequenas:
1. **Menu Hambúrguer (Drawer):** No celular, a barra superior de navegação (`Navbar`) agora possui um botão do lado esquerdo. Ao clicar, um menu escuro ("Gaveta" ou Drawer) desliza pela tela contendo os links para o Visão Geral, Pergaminhos, Banco, QG e Painel.
2. **Tamanho de Modais:** Ajustamos a altura máxima (`max-h-[90vh]`) de todos os modais do sistema (Oráculo, Faturas, Rateios, QG, Banco). Ao abrir no celular, o modal agora ganha uma barra de rolagem interna, garantindo que o cabeçalho e os botões de ação nunca fujam da tela principal.
3. **Menu Flutuante Agrupador (FAB Menu):** No Dashboard, os antigos botões soltos ("Invocar Oráculo", "Emitir Fatura", "Registrar Dano") foram todos fundidos num único Botão Mágico expansível no canto da tela. Ao passar o mouse (ou clicar no celular), as opções sobem com as etiquetas e os ícones, deixando a interface limpa e elegante e prevenindo erros de clique em telas menores.
4. **Alinhamento do Quartel General:** Ajustamos os formulários de cadastro do QG e do Banco da Guilda. Todos foram portados para Modais com largura de 95% ajustada para se moldarem exatamente como os "Forjas".
5. **Integração do Boss do Mês:** Removemos o banner horizontal gigante do "Boss do Mês" que poluía a tela do Dashboard e empurrava a Tabela de Loot para baixo. O Boss agora foi promovido a um "Card de Atributo" e foi perfeitamente encaixado na grade superior, lado a lado com a Vida, Stamina e Tesouro. Ele se transformou em um quadrado elegante de bordas vermelhas e ícone de caveira!
