# Getting Started

This guide explains how to install, configure and run the multi-provider terminal chatbot.

## Requirements

- Python 3.10 or newer.
- An API key for Anthropic, OpenAI or both.
- A hosted Supabase project for the RAG knowledge base (PostgreSQL + pgvector).
- Network access to the documented service URLs listed in the main README.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy the example file and fill in your own credentials. Never commit the `.env` file.

```bash
cp .env.example .env
```

Required variables:

- `CHAT_PROVIDER`: `anthropic` or `openai`, the provider used when the chat starts.
- `ANTHROPIC_API_KEY`: credential for the Anthropic API.
- `OPENAI_API_KEY`: credential for the OpenAI API; it is also required for RAG embeddings.
- `SUPABASE_URL`: HTTPS URL of the hosted Supabase project.
- `SUPABASE_SERVICE_KEY`: service key used by the ingestion and retrieval code.

Optional variables:

- `ANTHROPIC_MODEL` and `OPENAI_MODEL`: default model of each provider.
- `ANTHROPIC_BASE_URL` and `OPENAI_BASE_URL`: override the API endpoint of a provider.
- `CHAT_MODEL`: model used for the first conversation only.
- `CHAT_DB_PATH`: location of the SQLite file that stores saved chats.
- `DOCUMENTS_DIR`: folder scanned by the ingestion command.
- `RAG_TOP_K`: number of chunks retrieved per question, between 4 and 6 is the baseline.
- `RAG_SIMILARITY_THRESHOLD`: minimum relevance required to use a chunk.

## Running the chatbot

```bash
python main.py
```

The chat keeps accepting messages until you type `/exit`. Type `/help` inside the
chat to see every available command. You can also start the chat with an explicit
provider, model and skill:

```bash
python main.py --provider openai --model gpt-4o-mini --skill python-helper
```

## Useful checks

- `/status` shows the active provider, model, skill, context size and session id.
- `/providers` lists the providers compiled into the application.
- `/rag` shows whether the knowledge base is reachable.

## First troubleshooting step

If the chat refuses to start, the message tells you which environment variable is
missing. Fix the `.env` file and start the chat again; the process never exits
because of a configuration error.
