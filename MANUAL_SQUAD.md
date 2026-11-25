# 📘 Manual Operacional do Squad — Bússola Pública

Este guia prático orienta os 6 integrantes do squad **Bússola Pública** na configuração do ambiente local, no fluxo diário de trabalho com **Git e GitHub**, nas regras de proteção de custos/credenciais e na execução ordenada do cronograma de **14 dias**.

---

## 🧭 0. Primeira vez trabalhando em equipe com Git? Entenda em 1 minuto

Se você nunca participou de um projeto colaborativo no GitHub, não se preocupe — a lógica é bem simples. Pense no repositório como um **"caderno oficial"** onde cada integrante pega uma **"folha de rascunho"** para trabalhar sem risco de apagar ou quebrar o código do colega:

* **`main` (O Caderno Oficial):** guarda a versão estável e aprovada do projeto. Ninguém edita direto nela no dia a dia.
* **`branch` (Sua Folha de Rascunho):** quando você vai fazer uma tarefa, cria uma cópia isolada só sua (ex.: `feat/ingestao-camara`). Assim, os 6 integrantes podem programar ao mesmo tempo sem um atropelar o outro.
* **`commit` (Salvar um Ponto de Controle):** a cada avanço que você faz na sua *branch*, você salva um ponto de controle com uma mensagem curta do que foi feito.
* **`push` (Enviar seu Rascunho para a Nuvem):** envia seus *commits* do seu computador para a sua *branch* lá no GitHub.
* **Pull Request / PR (Pedido de Revisão):** quando terminar sua parte, você abre um PR no site do GitHub avisando o time: *"Terminei essa entrega, alguém revisa para juntarmos no caderno oficial?"*. Depois que 1 colega aprova, seu código entra na `main`.

> 💡 **Resumo:** você **nunca** quebra o projeto dos outros porque trabalha sempre na sua própria *branch* e só junta na `main` depois de testado e revisado.

---

## 👥 1. Divisão de Papéis & Frentes do Squad (6 Integrantes)

Para permitir trabalho paralelo sem sobreposição de arquivos, cada integrante atua em uma frente bem definida:

| Papel | Integrante | Entregas & Responsabilidades |
| :--- | :--- | :--- |
| **Integrante 1 — Tech Lead / Governança** | **Luiz Fernando** | • Setup da Fase 0 (Supabase, OpenAI restrita, repositório e proteção da `main`).<br>• Revisão e aprovação de Pull Requests.<br>• Suporte em Git/arquitetura e consolidação final (`README.md` + validação read-only). |
| **Integrantes 2 e 3 — Engenharia de Dados (ETL & DW)** | *Integrante 2*<br>*Integrante 3* | • **Etapa 1:** Extração da API da Câmara (`/proposicoes`, `/deputados`, `/partidos`, `/votacoes`, `/despesas`), paginação, *rate limit* e padronização.<br>• **Etapa 2:** Expansão do DDL (`dim_tempo`, `fato_votacoes`, `fato_despesas`), carga idempotente (`UPSERT`) e criação do usuário somente leitura (`bussola_reader`). |
| **Integrantes 4 e 5 — IA & FinOps** | *Integrante 4*<br>*Integrante 5* | • **Etapa 3:** Geração de embeddings (`text-embedding-3-small`) para 100% das proposições.<br>• Classificação temática por similaridade vetorial e acionamento seletivo do `gpt-4o-mini` **apenas** para temas críticos (`Tributário e Fiscal`, `Tecnologia e Inteligência Artificial`, `Saúde Pública`).<br>• Registro de tokens e custo estimado por execução. |
| **Integrante 6 — Automação & Alertas** | *Integrante 6* | • **Etapa 4:** Configuração da instância n8n do squad, importação/ajuste do workflow e integração com bot do Telegram.<br>• Validação de idempotência (`notificado_telegram = FALSE` → `TRUE`) e apoio na carga histórica da **Etapa 5**. |

---

## 💻 2. Configuração do Ambiente Local (Passo a Passo)

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/lufernasilva/bussola-publica.git
   cd bussola-publica
   ```

2. **Crie e ative o ambiente virtual Python (3.10+):**
   ```bash
   python -m venv .venv
   # Windows (PowerShell/CMD):
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure suas variáveis de ambiente:**
   * Copie `.env.example` e renomeie a cópia para `.env`.
   * Cole os valores reais enviados pelo Tech Lead no canal privado do squad.
   * **Regra de ouro:** nunca remova `.env` do `.gitignore` e nunca cole chaves reais dentro do `.env.example`.

---

## 🔀 3. Fluxo de Trabalho no Git (Obrigatório para Todos)

Sempre que for iniciar uma nova tarefa:

1. **Atualize sua `main` local:**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Crie uma *branch* para a sua frente:**
   * Padrão de nomes: `feat/<frente>-<tarefa>`, `fix/<descricao>` ou `docs/<descricao>`.
   * Exemplos: `feat/etl-proposicoes`, `feat/dw-upsert`, `feat/ia-embeddings`, `feat/n8n-telegram`.
   ```bash
   git checkout -b feat/sua-tarefa
   ```

3. **Desenvolva, teste localmente e salve seus commits:**
   ```bash
   git status
   git add <arquivos-alterados>
   git commit -m "feat: descreva objetivamente o que foi feito"
   ```

4. **Envie sua *branch* para o GitHub e abra o Pull Request:**
   ```bash
   git push -u origin feat/sua-tarefa
   ```
   * Acesse o repositório no GitHub, clique em **Compare & pull request**, descreva o que foi testado e solicite revisão de pelo menos **1 colega** (ou do Tech Lead).

---

## 💰 4. Regras de FinOps & Governança de Custos

A chave `bussola-publica-squad` da OpenAI possui restrição de escopo (`embeddings` e `chat/completions`) e orçamento controlado (meta < **US$ 0,50** no projeto):

1. **Desenvolvimento com amostras:** durante as Etapas 1 e 2, use os arquivos de `data/sample/` ou limites pequenos (`itens=10`) sem chamar a API da OpenAI.
2. **Embeddings em 100%, LLM apenas nos críticos:** use `text-embedding-3-small` para classificar todas as proposições; chame `gpt-4o-mini` **exclusivamente** nas proposições classificadas nos temas críticos definidos pelo squad.
3. **Cache / Idempotência no banco:** nunca reprocessar proposições que já possuam embedding, classificação ou resumo salvo no Supabase.
4. **Logs de consumo:** todo script de IA deve registrar no console/log a quantidade de itens processados, tokens consumidos e custo estimado.

---

## 📅 5. Roadmap de 14 Dias

| Etapa | Período | Responsáveis | Entregáveis Principais | Critério de Aceite |
| :--- | :--- | :--- | :--- | :--- |
| **Fase 0 — Setup & Destrave** | Dias 0–1 | Integrante 1 | Supabase inicializado (`00_fase0_init.sql`), chave OpenAI restrita, repositório protegido e manuais no ar. | ✅ **Concluída.** Todos os integrantes clonando e rodando local. |
| **Etapa 1 — Extração & Padronização** | Dias 2–4 | Integrantes 2 e 3 | Scripts em `src/` para coletar proposições, deputados, partidos, votações e despesas da API da Câmara. | Paginação funcional, tratamento de erros HTTP e JSON/DataFrame limpo. |
| **Etapa 2 — Modelagem DW & Read-Only** | Dias 4–7 | Integrantes 2 e 3 | Scripts SQL em `sql/` (`dim_tempo`, `fato_votacoes`, `fato_despesas`), carga `UPSERT` e role `bussola_reader`. | Reexecução sem duplicar registros no Supabase e role read-only validada. |
| **Etapa 3 — Camada de IA & FinOps** | Dias 7–10 | Integrantes 4 e 5 | Pipeline de embeddings (`text-embedding-3-small`) + resumo seletivo (`gpt-4o-mini`) + colunas de controle no banco. | 100% classificados por embedding, resumos só nos críticos e custo logado. |
| **Etapa 4 — Orquestração & Alertas** | Dias 10–12 | Integrante 6 | Workflow n8n exportado em `n8n/`, bot Telegram ativo e controle `notificado_telegram`. | Alerta entregue no Telegram sem disparos duplicados ao rodar 2x. |
| **Etapa 5 — Carga Histórica & Entrega** | Dias 12–14 | Todo o Squad (Coord. Int. 1 e 6) | Carga histórica de 30+ dias, agendamento ativo no n8n e atualização final do `README.md`. | Pipeline rodando ponta a ponta, métricas FinOps publicadas e banco read-only conferido. |

---

## ✅ 6. Checklist Rápido Antes de Abrir um PR

* [ ] Rodei `git status` e conferi que nenhum `.env` ou chave secreta está sendo enviado?
* [ ] Atualizei minha branch com a `main` mais recente (`git pull origin main` / `git merge main`) antes de abrir o PR?
* [ ] O código roda localmente sem erros usando apenas as variáveis documentadas em `.env.example`?
* [ ] Se alterei o banco, salvei o script SQL incremental na pasta `sql/`?
* [ ] Se alterei o workflow do n8n (Etapa 4+), exportei o `.json` atualizado para `n8n/`?