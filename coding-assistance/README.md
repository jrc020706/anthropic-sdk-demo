# AI-assisted development trace

This folder records how AI coding assistants were used to build this project. It is a
required deliverable of the challenge: every prompt sent to an AI coding assistant
during development is stored in `prompts.jsonl`.

## Files

| File | Contents |
| --- | --- |
| `README.md` | Which coding agents, models and AI tools were used and what they were used for |
| `prompts.jsonl` | One JSON object per prompt, newline delimited |

## Entry format

Each line of `prompts.jsonl` is a JSON object with at least these fields:

```json
{
  "timestamp": "2026-10-05T12:00:00+00:00",
  "agent": "OpenCode",
  "tool": "OpenCode CLI",
  "model": "mimo-v2.6-flash-free",
  "prompt": "Full text of the prompt sent to the assistant",
  "purpose": "Why the prompt was sent"
}
```

Optional fields are added when they carry useful context, for example
`"phase": "implementation"` or `"inputs": ["README.md"]`.

## Rules

- **No secrets.** API keys, tokens, passwords and `.env` values are never written to
  this log. If a prompt contained a credential, it is replaced by
  `"<redacted: never store secrets>"`.
- **Completeness.** One entry per prompt, in chronological order, covering the whole
  development history of the repository.
- **Language.** Entries keep the original language of the prompt; the metadata fields
  are written in English.

## Agents, models and tools used

### This repository

| Agent / tool | Model | Used for |
| --- | --- | --- |
| OpenCode (CLI coding agent) | `mimo-v2.6-flash-free` (MiMo-V2.6-Flash Free, provider `opencode`) | Reading the acceptance-criteria PDF, designing and writing the session/memory layer, the Supabase + pgvector RAG pipeline, the terminal commands, the skills documentation, `.env.example`, `requirements.txt` and the README |
| OpenCode (CLI coding agent) | `z-ai/glm-5.3` (provider `nvidia`) | Verifying the acceptance criteria offline, adding the free-tier providers (Groq, OpenRouter) and the free embeddings override, refreshing the README and `.env.example`, and removing the requirements PDF from the repository |
| OpenCode file and shell tools | n/a (harness tools) | Running the smoke tests, the ingestion preview and the CLI checks used to verify each acceptance criterion |
| `pdftotext` (Poppler) | n/a (not an AI tool) | Extracting the text of the acceptance-criteria PDF so the agent could read it (the PDF was removed from the repository after the alignment was verified) |

### Initial version of the project (commit `1ea5aae`, 2026-10-05)

| Agent / tool | Model | Used for |
| --- | --- | --- |
| Claude Code | Not recorded (see the gap below) | First version of the repository: Anthropic and OpenAI adapters behind one shared contract, the terminal chat with local skills, the adaptive system prompt, the skill creator/runner tooling and the `chat_app/` clean-architecture layout |

### Known gap

The verbatim prompt sent for commit `1ea5aae` and the exact model version used by
Claude Code were not preserved when that version was written. The available evidence
is the commit subject, `feat: Implement multi-provider chat application with skill
support`, which is stored in `prompts.jsonl` with `"prompt_verbatim": false` so the
entry is never mistaken for a real transcript.

To close the gap, replace that entry with the original prompt:

```bash
python - <<'EOF'
import json, pathlib
path = pathlib.Path("coding-assistance/prompts.jsonl")
entries = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
entries[3]["prompt"] = "paste the original prompt here"
entries[3]["model"] = "claude-sonnet-4-5"
entries[3]["prompt_verbatim"] = True
path.write_text("".join(json.dumps(e) + "\n" for e in entries))
EOF
```

## Verifying the log

```bash
# Number of recorded prompts
wc -l coding-assistance/prompts.jsonl

# Every entry must have the required fields
python -c "
import json, sys
required = {'timestamp', 'agent', 'model', 'prompt', 'purpose'}
for i, line in enumerate(open('coding-assistance/prompts.jsonl'), 1):
    entry = json.loads(line)
    missing = required - entry.keys()
    if missing:
        sys.exit(f'line {i} is missing {missing}')
print('prompts.jsonl is valid')
"

# No secrets in the log
grep -niE 'sk-[a-z0-9]|api[_-]?key.*=.*[a-z0-9]{12}|service_role' coding-assistance/prompts.jsonl || echo "no secrets found"
```
