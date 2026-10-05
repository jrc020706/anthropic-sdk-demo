# Multi-Provider Terminal Chatbot with Memory, RAG and AI-Assisted Development

A terminal chatbot that talks to **Anthropic** and **OpenAI** through one shared provider
contract, keeps a rolling window of the 10 most recent messages, stores complete
sessions in SQLite so they survive restarts, answers from a local document knowledge
base hosted in **Supabase (pgvector)**, and ships reusable skills plus a full log of
the AI prompts used to build it.

The requirements come from
[`Riwi_MultiProvider_Terminal_Chatbot_Acceptance_Criteria_Final.pdf`](Riwi_MultiProvider_Terminal_Chatbot_Acceptance_Criteria_Final.pdf);
section 10 maps the repository to that checklist.

---

## 1. Deployed services

The chatbot runs locally, but every service it consumes is a hosted service reachable
through a documented URL. No service dependency is localhost-only.

| Service | Purpose | URL | Environment variables |
| --- | --- | --- | --- |
| Anthropic API | Chat provider (required) | `https://api.anthropic.com` | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_BASE_URL` (optional) |
| OpenAI API | Chat provider + RAG embeddings (required) | `https://api.openai.com/v1` | `OPENAI_API_KEY`, `OPENAI_MODEL`, `EMBEDDING_MODEL`, `OPENAI_BASE_URL` (optional) |
| Supabase (PostgreSQL + pgvector) | Vector database for RAG (required for RAG) | `https://<project-ref>.supabase.co` | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_TABLE` (optional) |
| SQLite file | Saved chats, stored on your machine | local file `data/chats.db` | `CHAT_DB_PATH` (optional) |

Documentation of each service: [Anthropic docs](https://docs.anthropic.com/),
[OpenAI docs](https://platform.openai.com/docs/), [Supabase docs](https://supabase.com/docs).

No secret is written in this file. All credentials live in `.env`, which is ignored by git.

---

## 2. Setup

### Requirements

- Python 3.10+
- An Anthropic API key and an OpenAI API key
- A hosted Supabase project (free tier is enough) for the knowledge base

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If your interpreter was created with a Python version that is no longer installed,
keep the old environment as a backup and create a new one:

```bash
mv .venv .venv-respaldo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```env
CHAT_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

Every variable is documented inline in [`.env.example`](.env.example).

### Create the vector database (once per Supabase project)

1. Open your Supabase project → **SQL Editor** → **New query**.
2. Paste the contents of [`data/supabase/schema.sql`](data/supabase/schema.sql).
3. Run it. It creates the `documents` table, the HNSW index and the
   `match_documents` function.

---

## 3. Knowledge-base ingestion

Documents live in [`data/documents/`](data/documents/). Supported formats: `.md`,
`.markdown`, `.txt`, `.text` and `.pdf`.

```bash
# Embed and store every document (load -> chunk -> overlap -> embed -> store)
python ingest.py

# Show the chunk sizes and overlaps without calling any external service
python ingest.py --preview

# Drop the index first and ingest everything again
python ingest.py --rebuild

# Ingest a single document
python ingest.py --only getting-started.md

# Tune the chunking baseline (500-800 tokens, 10-20% overlap)
python ingest.py --chunk-tokens 700 --overlap 0.20
```

Each document prints one line: `[ok]`, `[skipped]` (unsupported type or empty file) or
`[error]`. A failed document never interrupts the rest of the ingestion.

Chunking defaults: **600 tokens per chunk** with **15% overlap**, snapped to paragraph,
line or sentence boundaries. Embeddings use `text-embedding-3-small` (1536 dimensions)
through the official OpenAI SDK. Every stored chunk carries its `source`, `document`,
`chunk_index` and `chunk_tokens` metadata.

---

## 4. Running the chatbot

One documented command:

```bash
python main.py
```

The chat accepts messages until you type `/exit`. The first line of the session shows
the active provider, model, skill, context size, session id and whether RAG is on.

Start it with explicit options if you want:

```bash
python main.py --provider openai --model gpt-4o-mini --skill python-helper
python main.py --max-tokens 1500 --history-limit 10
```

### Commands

| Command | What it does |
| --- | --- |
| `/help` | Show the command list |
| `/status` | Active provider, model, skill, context `n/10`, session id, RAG on/off |
| `/providers` | List the compiled providers |
| `/provider <name>` | Switch provider (`anthropic` / `openai`) and start a new conversation |
| `/model <name>` | Change the model of the current provider |
| `/memory` | Inspect the active 10-message context window |
| `/chats` | List saved sessions by stable id (active one marked `*`) |
| `/resume <session-id>` | Continue a saved session |
| `/skills` | List the installed skills |
| `/skill <name\|none>` | Enable a skill or disable it |
| `/rag` | Show knowledge-base status: stored chunks, top_k, threshold, embedding model |
| `/new` | Start a new conversation (the previous one stays saved) |
| `/exit` | Close the chat |

### Provider switching

The same conversation flow runs on both providers because they share one provider
contract; the conversation logic is never duplicated.

- Persistently: set `CHAT_PROVIDER=anthropic` or `CHAT_PROVIDER=openai` in `.env`.
- Per run: `python main.py --provider openai`.
- During the session: `/provider anthropic` (this starts a new conversation, so the
  provider stored in a saved session stays consistent).

### Saved chats and memory

- The active context is a rolling window of the **10 most recent user/assistant
  messages**. Older messages are dropped, and every model call sends only the system
  instructions plus that window.
- `/memory` prints the window content and its size.
- Complete sessions are stored in `data/chats.db` (SQLite) and survive restarts.
- `/chats` lists them with a stable id, provider, model, message count and update time.
- `/resume <session-id>` reloads the full stored history, rebuilds the active context
  from the last 10 messages, adopts the saved provider/model and writes new messages
  back to the same session.

---

## 5. Testing the RAG flow

1. **Ingest**: `python ingest.py` → every document must report `[ok]`.
2. **Check the index**: `python main.py`, then `/rag` → it must report the stored
   chunk count, the top_k (default 5) and the relevance threshold (default 0.20).
3. **Retrieve**: ask a question covered by the documents, for example
   *"How do I create the Supabase tables?"* or
   *"What does /resume rebuild the context from?"*. The answer must be followed by a
   `Sources:` line with the file name and its relevance score.
4. **No invention**: ask something outside the documents, for example
   *"What is the population of Bolivia?"*. The chatbot must answer that there is not
   enough information in the knowledge base instead of inventing content.
5. **Failure path**: remove `SUPABASE_URL` from `.env`, restart the chat and send a
   message. You get a `RAG warning` line and the conversation keeps working.

You can also inspect chunking without credentials: `python ingest.py --preview`.

### Offline verification (no credentials needed)

```bash
python tests/run_offline_checks.py
```

It checks the 10-message window, the persistence and `/resume` behaviour, the RAG
wiring (chunks and their source metadata reaching the system prompt), the recoverable
failure paths and the 500-800 token / 10-20% overlap chunking baseline.

---

## 6. Custom skills

Two reusable skills live in [`skills/`](skills/). Each `SKILL.md` documents its
**purpose**, **expected input**, **expected output**, **how to invoke** it and its
numbered instructions.

| Skill | Purpose | Typical input | Expected output |
| --- | --- | --- | --- |
| `python-helper` | Explain, write and debug Python code | A Python question, snippet or bug report | Diagnosis first, runnable code, explanation of the important parts |
| `sql-expert` | SQL queries, schema review and index tuning | A query, schema or performance problem | SQL first (uppercase keywords), explanation, dialect and index advice |

### Working demo

```bash
# Inside the chat
/skill python-helper
/skill sql-expert
/skill none

# Starting the chat with a skill
python main.py --skill python-helper

# One-off query without opening the chat
python run_skill.py --list
python run_skill.py --skill python-helper --prompt "How do I write a generator in Python?"
python run_skill.py --skill sql-expert --prompt "How do I index a table for reporting?"

# Inspect the installed skills
python setup_skill.py
```

### Creating a new skill

```bash
python create_skill.py
```

```bash
python create_skill.py \
  --name "docker-expert" \
  --desc "Docker and Docker Compose specialist" \
  --objective "Help build Dockerfiles and multi-container orchestration" \
  --rule "Always use official lightweight base images"
```

Skill names are kebab-case and are never overwritten by accident.

---

## 7. AI-assisted development trace

Everything about the coding assistants, models and tools used to build this project is
recorded in [`coding-assistance/`](coding-assistance/):

- [`coding-assistance/README.md`](coding-assistance/README.md) — which agents, models
  and tools were used and for what.
- [`coding-assistance/prompts.jsonl`](coding-assistance/prompts.jsonl) — one JSON line
  per prompt sent to an AI coding assistant, with `timestamp`, `agent`, `tool`,
  `model`, `prompt` and `purpose`.

No API key, token or password is stored in that log.

---

## 8. Project structure

```text
chat_app/
├── domain/
│   ├── models.py                 # ChatMessage, ProviderConfig, RetrievedChunk, SessionSummary
│   └── ports.py                  # ChatProvider, SessionStore, Retriever contracts
├── application/
│   ├── chat_session.py           # Conversation use case: 10-message window + RAG + persistence
│   ├── prompt_design.py          # System instructions (general, skill mode, RAG context)
│   └── skill_query.py            # One-off skill query
├── infrastructure/
│   ├── config.py                 # Environment variables and validation
│   ├── providers.py              # Anthropic and OpenAI adapters (official SDKs)
│   ├── session_store.py          # SQLite store for saved chats
│   ├── skill_manager.py          # Skill reading and creation
│   └── rag/
│       ├── loaders.py            # .md / .txt / .pdf readers + unsupported types
│       ├── chunking.py           # Token chunking with overlap and boundary snapping
│       ├── embeddings.py         # Official OpenAI embeddings endpoint
│       ├── vector_store.py       # Supabase + pgvector storage and similarity search
│       ├── retriever.py          # Query -> embed -> search -> top-k chunks with sources
│       └── ingestion.py          # Per-document load -> chunk -> embed -> store
└── presentation/
    ├── chat_cli.py               # Interactive terminal chat
    ├── ingest_cli.py             # Ingestion command line
    ├── skill_cli.py              # One-off skill query
    ├── create_skill_cli.py       # Interactive skill creator
    ├── setup_skill_cli.py        # Installed skill inspector
    └── composition.py            # Wires ports to adapters and collects warnings

main.py        # python main.py      -> interactive chat
ingest.py      # python ingest.py    -> knowledge-base ingestion
run_skill.py   # python run_skill.py -> one-off skill query
create_skill.py / setup_skill.py    # skill tooling
tests/run_offline_checks.py         # offline acceptance checks (no credentials)

data/
├── documents/                    # Knowledge-base source documents
├── supabase/schema.sql           # pgvector table, index and match_documents function
└── chats.db                      # Saved chats (created at run time, never committed)

skills/                           # Reusable custom skills
coding-assistance/                # AI development trace (README + prompts.jsonl)
```

The root modules `chat.py`, `config.py`, `providers.py` and `skill_manager.py` are kept
as facades so previous imports keep working.

---

## 9. Failure handling

Recoverable problems are printed in the terminal and **never terminate the chat**:

| Problem | Message you get |
| --- | --- |
| Missing `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | The exact variable to add to `.env` |
| Missing `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | Knowledge base disabled, chat keeps working |
| Provider or API failure | The provider error, and the session stays open |
| Missing Supabase table or `match_documents` | Pointer to `data/supabase/schema.sql` |
| Empty retrieval | The answer states there is not enough information |
| Unsupported document | `[skipped]` with the reason; the other files still ingest |
| SQLite failure | `Storage warning`, the chat continues in memory |
| Ctrl+C during a request | Request cancelled, session preserved |

---

## 10. Acceptance checklist

```bash
# 0. Offline checks: memory window, saved chats, /resume, RAG wiring, chunking
python tests/run_offline_checks.py

# 1. Runs from the terminal following this README
python main.py

# 2. Both providers share the same flow
/provider openai    # then /provider anthropic

# 3. Memory window and saved chats
/memory
/chats
/restart-free check: exit, run python main.py again, then /chats

# 4. RAG
python ingest.py
python main.py      # then /rag, ask a documented question, ask an unrelated one

# 5. Skills
python run_skill.py --skill python-helper --prompt "Explain list comprehensions"
python run_skill.py --list

# 6. AI trace
cat coding-assistance/prompts.jsonl

# 7. No secrets in the repository
grep -rniE "sk-[a-z0-9]{10}|service_key *= *['\"][a-z0-9]" --include="*.py" --include="*.md" .
```
