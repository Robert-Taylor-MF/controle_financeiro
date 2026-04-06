# Task Breakdown: Transaction Reconciliation Algorithm

- [x] Investigate the current invoice import logic in `services.py`
- [x] Implement the reconciliation algorithm (Path 2)
  - [x] Query for existing manual transactions with matching amount and date (within a small margin)
  - [x] Update matched transactions to 'FATURADO' status instead of creating duplicates
  - [x] Create new transactions only for unmatched invoice items
- [x] Add the +5 XP reward mechanism for manual transaction creation (if not already present)
- [x] Verify the implementation locally
- [x] Fix the Delete Button on the Dashboard (investigate JS/API call)
- [x] Add the Delete Button to the Extract (Pergaminhos)
### 3. Melhoria de UX no QG (Central de Cadastros)
- [x] Alterar layout do QG para remover as 3 colunas laterais de formulário.
- [x] Transformar os formulários de cadastro de Renda, Pessoas, Cartões e Categorias em Modais Flutuantes (mesmo padrão do Forjar).
- [x] Expandir o histórico/listagem de itens para ocupar 100% da largura da tela (Grid responsivo).
- [x] Replace browser alert with a custom themed RPG Modal for deletion
- [x] Investigate why Oracle import is not saving data (possible JSON parsing issue or DB transaction issue)
- [x] Investigate why Oracle import is not saving data (possible JSON parsing issue or DB transaction issue)
- [x] Change import redirect from Mural de Cobranças to Pergaminhos (Extrato Completo) with correct month filters
- [x] Investigate why Oracle import is not saving data (possible JSON parsing issue or DB transaction issue)
- [x] Change import redirect from Mural de Cobranças to Pergaminhos (Extrato Completo) with correct month filters
- [x] Fix JSON format parsing from Gemini response to ignore conversational text.
- [x] Implement Bulk Delete for Imported Invoices (Add UI button on Extrato based on filters, and API endpoint)
- [x] Implement Party Dashboard Tab in Visão Geral (show spending per person for the month)
- [x] Refactor "Enfrentar Boss do Mês" to block empty months and prevent infinite XP farming
- [x] Refactor "QG" (Central de Cadastros) to avoid cluttered side-by-side lists
- [x] Refactor Fatura Generation: Convert "Mural" into a floating Modal on the Dashboard and remove its dedicated page.
- [x] Refactor Rateio (Divide Expense): Convert "Dividir Saque" into a dynamic, auto-calculating Modal shared across Dashboard and Extrato.

### 4. Mobile Responsiveness & Polishing
- [x] Base Layout: Implement Mobile Navbar (Hamburger Menu + Drawer)
- [x] Floating Buttons: Adjust responsive padding and positioning for FABs
- [x] Modals: Ensure max-height and scrolling on modais to prevent overflowing off-screen
- [x] Fix any table filter overflows in Dashboard and Extrato

### 5. Floating Action Button (FAB) Menu
- [x] Group "Oráculo", "Emitir Fatura" and "Registrar Dano" into a single expandable FAB in Dashboard.
- [x] Make the sub-buttons discrete (icons with tooltips).
- [x] Adjust sizing for Desktop vs Mobile.

### 6. Boss Feature Relocation
- [x] Remove the large banner for "Boss do Mês" above the Loot table in the Dashboard.
- [x] Redesign it as a compact "Card" and integrate it into the top Summary Grid (Vitalidade, Stamina, Tesouro).
- [x] Adjust the grid layout to support 4 columns (`md:grid-cols-2 xl:grid-cols-4`).

### 7. Saldo Restante (Remaining Balance) Indicator
- [x] Calculate `saldo_restante` = `renda - total_gasto_pessoal` in `dashboard` view.
- [x] Add `saldo_restante` inside `views.py` context.
- [x] Render the new indicator next to "Mana Total" in `dashboard.html` header, styling it green if positive and red if negative.
