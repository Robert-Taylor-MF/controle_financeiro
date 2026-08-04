# Transaction Reconciliation Implementation Plan

## Goal Description
Implement an algorithm to automatically reconcile manually entered transactions with imported credit card invoice data. This prevents duplicate entries while preserving custom transaction descriptions and allowing users to gain daily XP for manual entries.

## Proposed Changes

### core/services.py
Modify `processar_fatura_pdf` to check for existing manual transactions before creating new ones:
1. For each item extracted by Gemini, query `Transacao.objects.filter(cartao=cartao, valor=item['valor'], status='PENDENTE')`.
2. Check if the `data_compra` matches the invoice item's date exactly or within a 1-day margin (since card operators sometimes shift the date slightly).
3. If a match is found:
   - Change `status` to 'FATURADO'.
   - Update `mes_fatura` and `ano_fatura` to match the imported invoice.
   - If the manual transaction had no category, apply the AI-suggested category.
   - Save the existing transaction instead of creating a new one.

### core/views.py
1. In the `dashboard` view, where manual expenses are created (`request.POST.get('acao') == 'nova_despesa'`), inject the +5 XP reward:
   - Find the system owner (`Pessoa.objects.filter(is_owner=True).first()`).
   - Call `titular.ganhar_xp(5)`.

## Proposed Changes - Fixing Deletion (Task 2)

### core/templates/base.html (or dashboard.html/extrato.html)
Look for the `deletarTransacao` JS function. If it's missing or broken, add/fix it. It should make a DELETE API call to `/api/deletar-transacao/<id>/` and then reload the page on success.

### core/templates/dashboard.html
Ensure the delete button correctly invokes `deletarTransacao(id)` and the JS function exists.
## Proposed Changes - Bulk Delete Invoices (Task 4)

### core/templates/extrato.html
Add a new red button "Obliterar Fatura Inteira" next to the filter button. This button will **only appear** if the user has filtered by a specific Month, Year, and Card.

### core/templates/base.html (or extrato.html)
Add a UI modal `modal-excluir-fatura` asking for confirmation before wiping out an entire month's invoice, and the necessary JS function `deletarFatura(mes, ano, cartao)`.

### core/urls.py
Add a new route: `path('api/deletar-fatura/<int:mes>/<int:ano>/<int:cartao_id>/', views.deletar_fatura, name='deletar_fatura')`

### core/views.py
Create the `deletar_fatura` function which will perform `Transacao.objects.filter(mes_fatura=mes, ano_fatura=ano, cartao_id=cartao_id).delete()` and return a success JSON response.
### core/templates/extrato.html
Add the delete button to the actions column in the table, replicating the design from the dashboard.

## Proposed Changes - Party Spending Dashboard (Task 5)

### core/views.py (`dashboard`)
Calculate the total spending for each person in the current filtered month/year.
Pass this data as a list of dictionaries (e.g. `gastos_party`) to the context. Also calculate the unassigned spending ("Loot sem dono").

### core/templates/dashboard.html
Implement a Tab Navigation system (`Visão Pessoal` vs `Visão da Party`) just below the month filters or header.
Wrap the current dashboard contents inside a `div id="aba-pessoal"`.
Create a new `div id="aba-party"` containing cards for each person, showing their avatar (if any), name, role, and the total amount they spent in the month.
Add Javascript (`mudarAbaDashboard`) to toggle between the two views.

## Proposed Changes - Boss Fight Refactor (Task 6)

### core/models.py
Add a new field `meses_fechados = models.TextField(blank=True, null=True, default="")` to the `Pessoa` model to store a comma-separated list of all months the user has defeated the boss.

### core/views.py (`enfrentar_boss_mes`)
1. Read `mes` and `ano` from `request.GET` instead of hardcoding `date.today()`, allowing the user to correctly fight the boss of the selected month.
2. Check if `Transacao.objects.filter(mes_fatura=mes, ano_fatura=ano)` has any records. If not, block the fight and return an error message "Não existem transações para prever o combate".
3. Calculate Mana vs Damage.
4. If victorious, check if `MM/YYYY` is inside `titular.meses_fechados`. If it is NOT, grant 200 XP, append `MM/YYYY` to the list, and show a success message. If it IS in the list, just show an info message that the Boss was defeated but the XP was already claimed.

### core/templates/dashboard.html
Update the `<a href="{% url 'enfrentar_boss_mes' %}">` link to include the current parameters: `?mes={{ mes_atual }}&ano={{ ano_atual }}`.

## Proposed Changes - QG Redesign (Task 7)

### core/templates/central_cadastros.html
To prevent horizontal squishing and vertical stretching as the databases grow:
1. **Remove the Side-by-Side (`lg:grid-cols-3`) Grid Pattern** inside all 4 tabs (`renda`, `pessoas`, `cartoes`, `categorias`).
2. **Move all Creation Forms into Modals**, similar to `banco_guilda.html`. We will create 4 hidden Modals (`modal-renda`, `modal-pessoa`, `modal-cartao`, `modal-categoria`).
3. **Add a Action Button** inside each tab (e.g., "Registrar Renda", "Recrutar Aliado", "Forjar Cartão", "Nova Categoria") aligned to the right, which triggers the respect modal.
4. **Expand the History Lists** to occupy 100% of the screen width using a responsive Grid of Cards (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`). This gives the items plenty of breathing room to grow symmetrically rows.
5. Create standard JS functions (`abrirModalCadastro(id)` and `fecharModalCadastro(id)`) to toggle these modals cleanly.

## Proposed Changes - Fatura Modal Refactor (Task 8)
**Goal:** Transform the "Mural de Cobranças" (Generate PDF Invoice) page into a floating modal button on the Dashboard, streamlining the user experience and decluttering the navigation bar.

### core/templates/base.html
- Remove the "Mural" link from the top navigation bar.

### core/templates/dashboard.html
- Add a floating button (e.g., "Gerar Fatura" or "Decreto") aligned to the right side of the screen (`bottom-40`), above the "Registrar Dano" button.
- Create a new hidden modal (`modal-fatura`) containing the `<form>` currently inside `cobrancas.html`.
- The form will POST/GET to `{% url 'fatura_pdf' %}` exactly as it did before.
- Implement JS to open and close this modal (`abrirModalFatura`, `fecharModalFatura`).

### core/urls.py
- Remove `path('cobrancas/', views.mural_cobrancas, name='mural_cobrancas')`.

### core/views.py
- Delete the `mural_cobrancas` view.

## Proposed Changes - Dynamic Rateio Modal (Task 9)
**Goal:** Transform the dedicated "Dividir Saque" (Ratear Transação) page into a dynamic Modal directly accessible from `Dashboard` and `Extrato` screens. Implement an auto-split (even distribution) calculation system among selected people.

### core/templates/base.html
- Add the hidden HTML block for the `modal-rateio` to the `base.html` footer so it can be called seamlessly from anywhere (Dashboard, Extrato, etc).
- The modal will contain:
  - Header: Original Expense description and Total Value (`valor_total`).
  - Dropdown to add `pessoas` (Alies) to the split.
  - A dynamic list container (`container-rateio`) where added people appear as input fields.
  - An "Auto-Dividir" logical engine in JavaScript.

### core/templates/base.html (JavaScript)
- `abrirModalRateio(transacao_id, descricao, valor_total)`: Opens the modal, resets the state, sets the target form action URL (`/dividir/{transacao_id}/`).
- `adicionarPessoaRateio()`: Grabs the selected person from the dropdown, adds them to the list of participants.
- `recalcularRateioIgualitario()`: Fires whenever a person is added or removed. It takes the `valor_total` and divides equally perfectly among all active participant inputs. Users can still manually override values later (which turns off the auto-calculation until another person is added/removed).

### core/templates/dashboard.html & core/templates/extrato.html
- Update the `<a href="{% url 'ratear_transacao' t.id %}">` buttons in the tables to `<button type="button" onclick="abrirModalRateio('{{ t.id }}', '{{ t.descricao|escapejs }}', '{{ t.valor|stringformat:'f' }}')">`. This prevents a page redirect and instead instantly opens the floating modal.

### core/urls.py
- Ensure the POST route `path('dividir/<int:transacao_id>/', views.ratear_transacao)` is intact to handle the form submission correctly.

### core/views.py
- Refactor `def ratear_transacao(request, transacao_id)` to only accept `POST` requests. If it receives a successful POST, redirect back to the `HTTP_REFERER` (so it works transparently whether the user was on the Dashboard or Extrato).
- Delete the old rendering logic that returned `ratear_transacao.html`.

### core/templates/ratear_transacao.html
- Delete this file since the screen is obsolete.

## Proposed Changes - Mobile Responsiveness (Task 10)
**Goal:** Make all screens and features fully accessible on mobile devices, preventing overflows and adding proper mobile navigation.

### core/templates/base.html
- **Mobile Navbar:** Add a hamburger menu button visible only on `lg:hidden` screens. Create a hidden mobile drawer (`div.fixed.inset-0.bg-slate-900`) that triggers via JS and contains all navigation links.
- **Top Profile Bar:** Ensure the profile picture and level badge don't push other elements off-screen.
- **Modals:** Ensure modals have `w-[95%]` instead of `w-full` on mobile, and `max-h-[85vh] overflow-y-auto` so they don't break height limits.

### core/templates/dashboard.html & extrato.html
- **Floating Buttons (Oráculo / Fatura):** Adjust the responsive positioning from `right-8` to `right-4 md:right-8` to save screen space on mobile.
- **Tables (Loot):** Ensure horizontal scroll logic (`overflow-x-auto`) works seamlessly and filters sit cleanly above the list.

### core/templates/central_cadastros.html & banco_guilda.html
- Ensure `grid-cols-1 md:grid-cols-3` logic is appropriately handling lists and inputs without horizontal overflow.

## Proposed Changes - Floating Action Button Menu (Task 11)
**Goal:** Clean up the UI from stacked floating buttons ("Registrar Dano", "Invocar Oráculo", "Emitir Fatura") by creating a unified FAB Menu that expands when clicked or hovered.

### core/templates/dashboard.html
- **Remove Individual Float Tracking:** Remove the independent `fixed bottom-* right-*` classes from the 3 buttons.
- **Implement FAB Container:** Create a single `div.fixed.bottom-6.right-4.md:bottom-8.md:right-8.flex.flex-col-reverse.items-end.gap-3.z-40.group`.
- **Primary Button:** The main button will just be a generic action icon (e.g., `<i data-lucide="plus"></i>` or `<i data-lucide="swords"></i>`).
- **Sub-buttons:** Inside the container, place the 3 original buttons inside a wrapper that starts hidden/collapsed. On hover (or focus/click), they animate upwards (`translate-y-0 opacity-100`).
- **Styling:** The sub-buttons will be smaller (e.g., `p-3` and `w-12 h-12`) and their texts will only appear next to them as tooltips, ensuring they look sleek and discrete on both mobile and desktop.

## Proposed Changes - Saldo Restante Indicator (Task 12)
**Goal:** Offer the user a realistic, real-time "Leftover Balance" (`Saldo Restante`) indicator for the active month, comparing injected Mana (Income) versus all personal registered expenses.

### core/views.py
- Inside `def dashboard(request):`, sum the 4 categoric personal expenses (`gasto_essencial`, `gasto_emocao`, `gasto_futuro`, `gasto_indefinido`) into `total_gasto_pessoal`.
- Calculate `saldo_restante = renda - total_gasto_pessoal`.
- Add `saldo_restante` into the return `contexto`.

### core/templates/dashboard.html
- Modify the `<header>` where `Mana Total (Líquido)` is presently displayed (around line 28).
- Change it into a Flex row grouping. Keep the `Mana Recebida` in purple.
- Add an adjacent block called `Saldo Restante`, displaying the {{ saldo_restante }}.
- Apply dynamic coloring: Green (`text-emerald-400`) if positive or zero, Red (`text-red-500`) if negative.
