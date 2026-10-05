# Skills, Configuration and Failure Handling

## What a skill is

A skill is a reusable Markdown file inside `skills/<skill-name>/SKILL.md`. It has
YAML-like frontmatter with `name` and `description`, followed by sections that
document the purpose, the expected input, the expected output, how to invoke it and
the numbered instructions the model must follow.

At run time the skill body is converted into system instructions. The rest of the
conversation flow is unchanged: the same provider contract, the same 10 message window
and the same persistence layer are used with or without a skill.

## The two skills shipped with this project

- `python-helper`: explains, writes and debugs Python code. Expected output is a short
  diagnosis, complete runnable code and an explanation of the important parts.
- `sql-expert`: SQL queries, schema reviews and index tuning. Expected output is the
  SQL statement first, then the explanation, the dialect considered and performance
  advice.

## Invoking a skill

```bash
# Enable a skill inside the chat
/skill python-helper

# Disable it again
/skill none

# Start the chat with a skill already enabled
python main.py --skill sql-expert

# Run a single query with a skill, without opening the chat
python run_skill.py --skill sql-expert --prompt "How do I index a table for reporting?"

# List the installed skills
python run_skill.py --list
python setup_skill.py
```

## Creating a new skill

```bash
python create_skill.py
```

or non-interactively:

```bash
python create_skill.py \
  --name "docker-expert" \
  --desc "Docker and Docker Compose specialist" \
  --objective "Help build Dockerfiles and multi-container orchestration" \
  --rule "Always use official lightweight base images"
```

Skill names are kebab-case and are never overwritten: choosing an existing name
returns an error instead of replacing the file.

## Configuration rules

All credentials come from environment variables. No API key, token or password is
written in the source code, in the documentation or in the AI development log. The
repository ships `.env.example` with every required variable and placeholder values
only.

## Failure handling

Recoverable problems are reported in the terminal and never terminate the chat:

- Missing credential: the message names the exact variable to add to `.env`.
- Provider or API failure: the error is printed and the conversation stays open.
- Missing Supabase table or function: the message points to `data/supabase/schema.sql`.
- Empty retrieval: the answer states that there is not enough information.
- Unsupported document: the file is skipped with its reason and the remaining files
  are still ingested.
- Storage failure: the chat keeps working in memory and prints a storage warning.

Pressing Ctrl+C during a request cancels that request only; the session stays open and
the stored history is preserved.
