# 📘 Manual de Execução do Squad — Bússola Pública (Dia 0 ao Dia 14)

Guia prático passo a passo para os 6 membros do squad executarem o projeto em paralelo sem bloqueios, prevenindo erros mapeados na Prova de Conceito (PoC).

---

## 🛠️ Checklist Pré-Kickoff

### Todos os 6 membros:
* VS Code instalado
* Git configurado + conta no GitHub
* Python 3.10+ instalado

### 1 responsável cria e compartilha no privado (via `.env`):
* Projeto no **Supabase** (PostgreSQL)
* Chave de API na **OpenAI Platform** (crédito pré-pago de US$ 5 é mais que suficiente; consumo estimado < US$ 0,50)
* Workspace no **n8n Cloud** (trial 14 dias) ou instância local via Docker

---

## 🚀 Etapa 0 — Estruturação (Dia 0 — Todos Juntos)

1. **Subir estrutura inicial na `main`:** descompactar este starter pack no repositório oficial e realizar o commit inicial contendo `sql/`, `src/`, `data/sample/`, `n8n/`, `docs/`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md` e `MANUAL_SQUAD.md`.
2. **Criar tabelas no Supabase:** abrir o **SQL Editor** do Supabase e executar `sql/create_tables.sql`.
3. **Gerar amostras iniciais (`data/sample/`):** rodar `python -m src.extract_camara` para baixar 1 página de cada endpoint e commitar os arquivos `*_sample.json` em `data/sample/`. Isso libera as equipes de ETL, IA e n8n imediatamente.

**Critério de Pronto:** Repositório estruturado na `main` + tabelas criadas no Supabase + arquivos de amostra em `data/sample/`.

---

## 📋 Etapas Paralelas (Dias 1 a 10)

### Etapa 1 — README, Convenções e Governança (Pessoa 1 | Dias 1–2)
* Atualizar `README.md` com o link do repositório e regras de contribuição.
* Garantir que ninguém faça push direto na `main` após a Etapa 0.
* Padrão de branches: `feat/dw-supabase`, `feat/extract-camara`, `feat/ia-finops`, `feat/n8n-telegram`, `docs/pitch-final`.

### Etapa 2 — Modelagem DW no Supabase (Pessoa 2 | Dias 1–2)
* Validar todas as 6 tabelas (`dim_partidos`, `dim_deputados`, `dim_tempo`, `fato_proposicoes`, `fato_votacoes`, `fato_despesas`).
* Confirmar `tema_ia VARCHAR(120)` e `notificado_telegram BOOLEAN DEFAULT FALSE` na `fato_proposicoes`.
* Rodar `sql/create_readonly_user.sql` (ajustando a senha) para criar o usuário de leitura dos avaliadores.
* Validar `python -m src.db_connection`.

### Etapa 3 — Ingestão e Camada de IA (Pessoas 3 e 4 | Dias 3–7)
* **Pessoa 3 (Ingestão):** alterar `apenas_amostra=False` e `dias=35` em `src/extract_camara.py` para popular `data/bronze/` com histórico mínimo de 30 dias dos 5 endpoints (`/proposicoes`, `/partidos`, `/deputados`, `/votacoes`, `/deputados/{id}/despesas`) e rodar `python -m src.pipeline_etl`.
* **Pessoa 4 (IA & FinOps):** refinar `TEMAS_REFERENCIA` e `TEMAS_CRITICOS` em `src/ai_layer.py`, registrar consumo de tokens/custo da OpenAI e validar a qualidade dos resumos executivos de 3 linhas.

### Etapa 4 — Bot Oficial e Fluxo n8n (Pessoa 5 | Dias 8–10)
* Criar o bot oficial no `@BotFather`, adicioná-lo ao grupo/canal do squad e **promovê-lo a Administrador**.
* Obter o `Chat ID` negativo do grupo/canal e configurar as credenciais do Postgres e Telegram no n8n.
* Importar `n8n/bussola_publica_workflow_template.json` no n8n, mantendo o `Schedule Trigger` desativado durante os testes manuais.
* Executar testes manuais, confirmar que `notificado_telegram` muda para `TRUE` e exportar o `.json` atualizado (sem credenciais) para `n8n/`.

---

## ✅ Etapa 5 — Validação Coletiva e Agendamento (Pessoa 6 + Todos | Dias 11–14)

* **Pessoa 6:** gerar diagrama do pipeline no Excalidraw, consolidar prints (Supabase com 30+ dias, execução verde no n8n, alerta no Telegram), preencher os dados de leitura no `README.md` e montar os 6 slides seguindo `docs/ROTEIRO_PITCH_6_SLIDES.md`.
* **Todo o Squad:** executar teste integrado ponta a ponta, ativar o `Schedule Trigger` no n8n e revisar o PR final antes da entrega.

---

## 🛡️ Lições Aprendidas da PoC (Erros Já Prevenidos)

1. **Truncamento de texto na coluna `tema_ia`:** já prevenido com `VARCHAR(120)` no `create_tables.sql`.
2. **Expressão `undefined` no `UPDATE` final do n8n:** o nó `Postgres - Marcar Notificado` já referencia explicitamente `$('Postgres - Buscar Pendentes').item.json.id_proposicao` em vez de `$json.id_proposicao` (que vem do retorno do Telegram).
3. **Permissão do Bot no Telegram:** o bot precisa receber `/start` no privado e ser **Administrador** no grupo/canal antes do primeiro disparo.
4. **Disparos duplicados em testes:** testar sempre com `Schedule Trigger` desativado e validar a atualização da flag `notificado_telegram = TRUE`.
