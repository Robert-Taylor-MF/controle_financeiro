# 🖥️ Módulo Desktop Portátil - Controle Financeiro

Este módulo permite executar o sistema **Controle Financeiro Gamificado** como um aplicativo Desktop nativo do Windows, eliminando a necessidade de janelas pretas de terminal (CMD) e abrindo a interface diretamente em uma janela própria.

---

## 📁 Estrutura do Módulo (`portatil/`)

* **`desktop_app.py`**: Ponto de entrada do aplicativo Desktop. Inicia o servidor em segundo plano e abre a janela nativa com `PyWebView`.
* **`build_exe.py`**: Script automatizado para compilar a aplicação em um executável portátil (`.exe`) via `PyInstaller`.
* **`dist/`**: Pasta gerada após a compilação contendo a versão executável final pronta para uso ou transporte em pendrive.

---

## 🚀 Como Executar em Modo de Desenvolvimento

Caso queira rodar a versão Desktop diretamente pelo Python sem compilar:

```cmd
.\venv\Scripts\python.exe portatil\desktop_app.py
```

---

## 🛠️ Como Gerar o Executável Portátil (`.exe`)

Para gerar a versão empacotada que funciona em qualquer computador Windows sem abrir terminal:

1. Execute o script de build:
   ```cmd
   .\venv\Scripts\python.exe portatil\build_exe.py
   ```

2. Ao finalizar a compilação, o aplicativo estará pronto no caminho:
   ```
   portatil\dist\MoneyQuest\MoneyQuest.exe
   ```

3. Você pode copiar a pasta `MoneyQuest` para um pendrive ou mover para qualquer diretório. Bastará dar um **duplo clique no `MoneyQuest.exe`** para iniciar o sistema!

