-- RAG schema for the multi-provider terminal chatbot.
-- Run this file once in the Supabase SQL editor (Dashboard -> SQL Editor -> New query).
-- It is safe to re-run: every statement uses IF NOT EXISTS or OR REPLACE.

-- 1. pgvector extension ------------------------------------------------------
create extension if not exists vector;

-- 2. Document chunks ---------------------------------------------------------
create table if not exists documents (
    id         bigserial primary key,
    content    text        not null,
    metadata   jsonb       not null default '{}'::jsonb,
    embedding  vector(1536) not null,
    created_at timestamptz not null default now()
);

-- Approximate index for cosine similarity searches.
create index if not exists documents_embedding_idx
    on documents using hnsw (embedding vector_cosine_ops);

-- Row Level Security: no policy is defined, so only the service role
-- (which bypasses RLS) can read or write this table.
alter table documents enable row level security;

-- 3. Similarity search -------------------------------------------------------
-- Returns the closest chunks with their source metadata and a similarity score
-- between 0 and 1, ordered from most to least relevant.
create or replace function match_documents(
    query_embedding vector(1536),
    match_count     integer default 5
)
returns table (
    id         bigint,
    content    text,
    metadata   jsonb,
    similarity float
)
language sql
stable
as $$
    select d.id,
           d.content,
           d.metadata,
           1 - (d.embedding <=> query_embedding) as similarity
      from documents d
     order by d.embedding <=> query_embedding
     limit greatest(match_count, 1);
$$;

-- 4. Handy maintenance queries -----------------------------------------------
-- Count indexed chunks:
--   select count(*) from documents;
-- Remove one document (used by re-ingestion):
--   delete from documents where metadata->>'source' = 'documents/getting-started.md';
-- Clear the whole knowledge base (python ingest.py --rebuild):
--   delete from documents;
