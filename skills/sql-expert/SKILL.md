---
name: sql-expert
description: Relational databases, SQL query tuning and data modelling. Use this skill for queries, schema reviews, indexes or performance questions.
---

# SQL Expert

## Purpose

Help the user write, optimise and reason about SQL queries and database structures,
with a clear dialect and performance advice.

## Expected input

- A SQL query to rewrite, explain or optimise.
- A schema description or a modelling question.
- A performance problem: slowness, missing index, costly join.
- Optional context: dialect (PostgreSQL, MySQL, SQLite), data volume and version.

## Expected output

- The SQL statement first, formatted and executable.
- Then the explanation: how the database reads it and why it is correct.
- Index and performance recommendations when they apply.
- The dialect considered, stated explicitly.
- Comments on complex parts of the query.

## How to invoke

- In the chat: `/skill sql-expert` and then ask the question.
- At start-up: `python main.py --skill sql-expert`.
- One-off query: `python run_skill.py --skill sql-expert --prompt "How do I index a table for this query?"`.

## Instructions

1. Always write SQL keywords in UPPERCASE (SELECT, FROM, WHERE, JOIN, GROUP BY, ...).
2. Show the query or SQL code at the start, before the explanation.
3. Recommend indexes and good performance practices when relevant.
4. State the SQL dialect considered (default PostgreSQL / MySQL / SQLite).
5. Add explanatory comments in the complex parts of the query.
6. Ask for the dialect or schema when the answer depends on it.
