# Controle Financeiro Gamificado

Um sistema de controle financeiro gamificado desenvolvido em **Django**. Este projeto tem como o objetivo engajar o usuário no controle de suas finanças transformando os gastos e economias em uma jornada interativa com elementos de RPG, como o sistema de *Boss Combat*.

## Funcionalidades
- Controle de receitas e despesas
- Dashboard gamificado de fácil visualização
- Sistema de *Boss Combat* com cartões compactos em grade para maximizar espaço no painel e usabilidade.
- Interface responsiva com foco no fluxo mobile ( Hamburger menu, Floating Action Buttons unificados, e sistema de modais flutuantes simplificados para todos os formulários).

## Requisitos
- **Python 3.x**
- Sistema Operacional Microsoft Windows (para uso nativo dos scripts de automação `.bat`)

## Instalação e Configuração (<kbd>Ambiente Zero</kbd>)
Um script automatizado já foi preparado para criar o ambiente limpo em novas máquinas:
1. Clone este repositório.
2. Dê um duplo clique ou execute no terminal o arquivo **`install.bat`**.

O script irá, em sequência:
- Criar automaticamente o ambiente virtual local (`venv`).
- Instalar e atualizar as dependências definidas no `requirements.txt`.
- Executar todas as *migrations* do projeto criando a arquitetura de base de dados SQLite limpa do zero.
- Questionar o usuário se deseja criar um Super Usuário administrador neste exato instante (Recomendado).

## Executar o Projeto
Para iniciar ativamente a aplicação:
- Execute o script **`run.bat`**.

Isto ativará o ambiente e acionará o servidor de produção focado em Windows **Waitress**, e a aplicação residirá no endereço: [http://localhost:8000](http://localhost:8000).

## Arquitetura Resumida
- `core/`: Engloba as aplicações da lógica principal do Game Financier, lógica de controle e sistema de UI Modal flutuante.
- `setup/`: Ponto de entrada das configurações (`settings.py`, `urls.py`, Servidor de Gateway WSGI).
- `db.sqlite3`: Arquivo de banco de dados gerado após a instalação.

## Stack
- Framework de Backend: **Django**
- Servidor de Produção Win: **Waitress**
- Banco Padrão: **SQLite3**
