# Providers, Memory and Saved Chats

This document describes how the chatbot talks to several LLM providers while keeping
one single conversation implementation.

## One provider contract

The application defines a single provider contract in the domain layer. It receives a
list of messages, a system prompt and a token budget, and returns text. Every provider
adapter implements that contract, so the conversation logic is written only once.

Two adapters are required by the challenge:

- `AnthropicProvider`, built on the official Anthropic Python SDK.
- `OpenAIProvider`, built on the official OpenAI Python SDK.

Both adapters normalise their differences before returning: the Anthropic SDK returns
text blocks that are concatenated, while the OpenAI SDK returns a single message
content. Provider specific errors are converted into one recoverable error type that
the terminal prints without closing the application.

## Switching providers

Switch providers at any moment with `/provider openai` or `/provider anthropic`.
Changing the provider starts a new conversation, because the provider and model of a
saved session must stay consistent. The active provider and model are always visible
in `/status`.

## The 10 message context window

The active context is a rolling window of the 10 most recent user and assistant
messages. When a new pair of messages would push the window past 10, the oldest
message is removed. Every model call sends exactly two things: the system
instructions and that window. Old messages are never sent again, so the token cost of
a long conversation stays constant.

Use `/memory` at any time to inspect the window content and its size.

## Saved chats

Complete sessions are stored in a local SQLite file, `data/chats.db` by default. The
file survives application restarts, and the directory is ignored by git.

- `/chats` lists every saved session with its stable id, provider, model, message count
  and last update time. The active session is marked with an asterisk.
- `/resume <session-id>` continues a saved session. The chat reloads the full stored
  history, rebuilds the active context from the last 10 messages and writes new
  messages back to the same session.
- `/new` starts a new session and keeps the previous one stored.

Session ids are short, stable hexadecimal strings, so they are easy to copy and paste
into `/resume`.
