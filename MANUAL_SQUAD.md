# Manual de Operação e Guia Prático — Squad Bússola Pública

Este guia prático orienta os 6 integrantes do squad **Bússola Pública** na configuração do ambiente local, no fluxo diário de trabalho com **Git e GitHub**, nas regras de proteção de custos/credenciais e na execução ordenada das etapas do cronograma de **14 dias**.

---

## 0. Primeira vez trabalhando em equipe com Git? Entenda em 1 minuto

Se você nunca participou de um projeto colaborativo no GitHub, não se preocupe — a lógica é bem simples. Pense no repositório como um **"caderno oficial"** onde cada integrante pega uma **"folha de rascunho"** para trabalhar sem risco de apagar ou quebrar o código do colega:

* **`main` (O Caderno Oficial):** guarda a versão estável e aprovada do projeto. Ninguém edita direto nela no dia a dia.
* **`branch` (Sua Folha de Rascunho):** quando você vai fazer uma tarefa, cria uma cópia isolada só sua (ex.: `feat/ingestao-camara`). Assim, os 6 integrantes podem programar ao mesmo tempo sem um atropelar o outro.
* **`commit` (Salvar um Ponto de Controle):** a cada avanço que você faz na sua *branch*, você salva um ponto de controle com uma mensagem curta do que foi feito.
* **`push` (Enviar seu Rascunho para a Nuvem):** envia seus *commits* do seu computador para a sua *branch* lá no GitHub.
* **Pull Request / PR (Pedido de Revisão):** quando terminar sua parte, você abre um PR no site do GitHub avisando o time: *"Terminei essa entrega, alguém revisa para juntarmos no caderno oficial?"*. Depois que 1 colega aprova, seu código entra na `main`.

> **Resumo:** você **nunca** quebra o projeto dos outros porque trabalha sempre na sua própria *branch* e só junta na `main` depois de testado e revisado.

---

## 1. Visão Geral e Status Atual da Infraestrutura (Fase 0 Concluída)

Para evitar consumo antecipado de créditos de IA, disparos acidentais ou atropelamento de etapas, o ambiente inicial já foi preparado de forma enxuta:

* **Banco de Dados (Supabase / PostgreSQL):** limpo (`DROP IF EXISTS ... CASCADE`) e inicializado apenas com o **DDL enxuto da Fase 0** (`dim_partidos`, `dim_deputados` e `fato_proposicoes` com colunas essenciais). Tabelas e colunas de IA, notificações, votações e despesas serão adicionadas incrementalmente nas respectivas etapas.

* **OpenAI API (`bussola-publica-squad`):** chave dedicada criada com permissões **Restritas** apenas para `/v1/embeddings` (`text-embedding-3-small`) e `/v1/chat/completions` (`gpt-4o-mini`). **Não rode scripts de IA em lote** antes da validação da Etapa 3.

* **Automação (n8n + Telegram):** reservada para as Etapas 4 e 5. Nenhum workflow ou agendamento automático está ativo neste momento.

---

## 2. Passo a Passo: Configuração do Ambiente Local

Siga estes passos apenas uma vez ao entrar no projeto:

### Passo 1 — Pré-requisitos instalados na máquina

* **Git** (`git --version`)

* **Python 3.10+** (`python --version` ou `python3 --version`)

* **VS Code** (recomendado com as extensões *Python* e *GitLens*)

### Passo 2 — Clonar o repositório oficial

No terminal, entre na pasta onde guarda seus projetos e execute:

```bash
git clone <URL_DO_REPOSITORIO_DO_SQUAD>
cd bussola-publica
```

### Passo 3 — Criar e ativar o ambiente virtual Python (`.venv`)

Nunca instale pacotes no Python global da sua máquina. Crie um ambiente virtual isolado:

* **Linux / macOS:**

  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

* **Windows (PowerShell):**

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```

  *(Se o PowerShell bloquear a execução de scripts, rode antes: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

Com o `(.venv)` ativo no terminal, instale as dependências do projeto:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Passo 4 — Configurar as variáveis de ambiente (`.env`)

Crie o seu arquivo `.env` local a partir do modelo versionado:

```bash
cp .env.example .env
```

Abra o `.env` no VS Code e preencha com as credenciais compartilhadas no canal privado do squad:

```env
# Banco de Dados (Supabase)
DATABASE_URL=postgresql://postgres.[PROJETO]:[SENHA]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres

# OpenAI (Chave restrita bussola-publica-squad - usar apenas quando autorizado na Etapa 3)
OPENAI_API_KEY=sk-proj-...

# Telegram (Usar apenas na Etapa 4+)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

> **Atenção:** O arquivo `.env` está listado no `.gitignore`. **Nunca** remova essa regra nem force o envio desse arquivo para o GitHub.

### Passo 5 — Trabalhar com amostras leves (`data/sample/`)

Durante o desenvolvimento das suas funções, teste primeiro usando os arquivos de amostra em `data/sample/` (~15 registros), sem disparar requisições pesadas na API da Câmara nem chamadas em lote na OpenAI.

---

## 3. Guia Prático: Como Trabalhar no GitHub (Sem Conflitos)

Para 6 pessoas trabalharem juntas sem sobrescrever o código umas das outras, seguimos o fluxo **Feature Branch + Pull Request (PR)**.

### Regras de Ouro do Git

1. **A branch `main` é protegida:** nunca codifique nem execute `git push origin main` diretamente. Toda alteração entra via **Pull Request**.

2. **Uma branch por tarefa/etapa:** crie uma branch com prefixo padronizado e nome objetivo:

   * `feat/` para novas funcionalidades (ex.: `feat/ingestao-camara`, `feat/dw-schema-upsert`, `feat/ia-embeddings-llm`, `feat/n8n-workflow`)

   * `fix/` para correções de bugs (ex.: `fix/paginacao-api`)

   * `docs/` para documentação (ex.: `docs/atualizacao-readme`)

3. **Commits pequenos e semânticos:** prefira vários commits claros e testados a um único commit gigante no fim do dia.

4. **Segredos jamais sobem:** nunca versione `.env`, chaves de API, senhas ou arquivos locais temporários.

### Ciclo Diário de Trabalho (Passo a Passo)

#### A) Antes de começar qualquer tarefa nova: sincronize sua `main` local

```bash
git checkout main
git pull origin main
```

#### B) Crie e entre na sua nova branch de trabalho

```bash
git checkout -b feat/nome-da-sua-tarefa
```

#### C) Desenvolva, valide o `git status` e salve seus commits

Antes de adicionar arquivos ao commit, **sempre** confira `git status` para garantir que nenhum `.env` ou arquivo temporário entrou:

```bash
git status
git add .
git commit -m "feat: implementa coleta paginada de proposicoes da Camara"
```

#### D) Envie sua branch para o GitHub

```bash
git push -u origin feat/nome-da-sua-tarefa
```

*(Nos próximos commits da mesma branch, basta rodar `git push`.)*

#### E) Abra um Pull Request (PR) no GitHub

1. Acesse o repositório no GitHub e clique em **Compare & pull request**.

2. Confira se a direção está correta: **`base: main` ← `compare: feat/nome-da-sua-tarefa`**.

3. Preencha uma descrição curta informando:

   * O que foi alterado;

   * Como testar localmente;

   * Se exige algum ajuste de `.env` ou execução de script SQL.

4. Avise no grupo do squad para que **pelo menos 1 integrante revise e aprove** o PR em até **24h**.

5. Após o merge na `main`, delete a branch remota pelo botão no GitHub (e localmente com `git branch -d feat/nome-da-sua-tarefa`).

### Situações Comuns no Dia a Dia (Como Resolver)

#### 1. Colegas atualizaram a `main` enquanto eu ainda trabalho na minha branch

Traga as novidades da `main` para dentro da sua branch para evitar conflitos grandes no final:

```bash
git checkout main
git pull origin main
git checkout feat/nome-da-sua-tarefa
git merge main
```

*Se o VS Code indicar conflito em algum arquivo:*

1. Abra o arquivo marcado com conflito no VS Code.

2. Escolha entre *Accept Current Change*, *Accept Incoming Change* ou combine ambos os trechos manualmente.

3. Salve o arquivo, teste o código e finalize o merge:

   ```bash
   git add .
   git commit -m "chore: resolve conflitos com main"
   ```

#### 2. Esqueci e comecei a editar código direto na `main` (antes de commitar)

Basta criar a branch antes de commitar — suas alterações não commitadas vão junto para a nova branch:

```bash
git checkout -b feat/nome-da-sua-tarefa
```

#### 3. Quero descartar alterações locais que deram errado em um arquivo

```bash
git checkout -- caminho/do/arquivo.py
```

---

## 4. Plano Colaborativo e Roadmap (14 Dias)

### Fase 0 — Setup Inicial e Amostra (Dias 0–1)

* [x] Limpeza do banco Supabase e criação das tabelas base (`dim_partidos`, `dim_deputados`, `fato_proposicoes`).

* [x] Criação da chave OpenAI restrita (`bussola-publica-squad`).

* [ ] Subir estrutura inicial do repositório e amostra leve (~15 registros) em `data/sample/`.

### Etapa 1 — Extração e Padronização (Dias 2–4)

* Implementar o coletor em `src/` para consultar proposições, deputados e partidos na API Dados Abertos da Câmara.

* Tratar paginação, limites de requisição e padronização de colunas antes da carga.

### Etapa 2 — Modelagem DW Completa e Acesso Read-Only (Dias 4–7)

* Criar scripts SQL incrementais em `sql/` (`ALTER TABLE` / `CREATE TABLE`) para adicionar `dim_tempo`, `fato_votacoes`, `fato_despesas` e colunas auxiliares.

* Implementar carga idempotente (`UPSERT` / `ON CONFLICT`) no Supabase.

* Criar o usuário/role **somente leitura (`SELECT`)** no Supabase para consulta e avaliação final.

### Etapa 3 — Camada de IA Híbrida e FinOps (Dias 7–10)

* Adicionar colunas de enriquecimento (`tema_ia`, `similaridade_tema`, `is_tema_critico`, `resumo_executivo`).

* Rodar classificação temática de 100% das proposições via `text-embedding-3-small` (similaridade de cosseno).

* Acionar `gpt-4o-mini` **exclusivamente** para proposições classificadas em temas críticos, registrando consumo de tokens e custo estimado.

### Etapa 4 — Orquestração e Alertas Idempotentes (Dias 10–12)

* Subir instância do n8n do squad e importar o workflow versionado em `n8n/`.

* Configurar o bot oficial do Telegram no grupo do squad e validar disparos apenas para registros com `is_tema_critico = TRUE` e `notificado_telegram = FALSE`, marcando `notificado_telegram = TRUE` após o envio.

* Manter o `Schedule Trigger` desligado durante testes e exportar qualquer ajuste do fluxo em `.json` para a pasta `n8n/` via PR.

### Etapa 5 — Carga Histórica (30+ Dias), Validação e Entrega (Dias 12–14)

* Executar carga histórica completa (30+ dias) e rodar o fluxo ponta a ponta.

* Ativar o agendamento no n8n após validação dos alertas.

* Testar o acesso **somente leitura** do Supabase e atualizar o `README.md` com métricas FinOps, arquitetura final e evidências.

---

## 5. Checklist Rápido Antes de Abrir um PR

* [ ] Rodei `git status` e conferi que nenhum `.env` ou chave secreta está sendo enviado?

* [ ] Atualizei minha branch com a `main` mais recente (`git merge main`) antes de abrir o PR?

* [ ] O código roda localmente sem erros usando apenas as variáveis documentadas em `.env.example`?

* [ ] Se alterei o banco, salvei o script SQL incremental na pasta `sql/`?

* [ ] Se alterei o workflow do n8n (Etapa 4+), exportei o `.json` atualizado para `n8n/`?