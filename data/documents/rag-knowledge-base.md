# RAG Knowledge Base

Retrieval augmented generation (RAG) lets the chatbot answer from local documents
instead of guessing. The pipeline is: documents, chunking with overlap, embeddings,
vector search, top chunks, model context.

## Documents and formats

Documents live in `data/documents/`. The loader accepts Markdown (`.md`,
`.markdown`), plain text (`.txt`, `.text`) and PDF (`.pdf`). Any other extension is
reported as an unsupported document and skipped with a readable message; the rest of
the ingestion continues normally.

A PDF is read page by page and empty pages are discarded. A PDF without extractable
text, such as a scanned image, is reported instead of silently producing an empty
index.

## Chunking with overlap

Chunking happens before embeddings. The default target is 600 tokens per chunk, which
sits inside the recommended 500 to 800 token range, and the default overlap is 15
percent of the chunk size, inside the recommended 10 to 20 percent range.

The splitter slides a window over the document and snaps its right edge to the closest
paragraph, line or sentence boundary, so chunks follow the structure of the document
instead of cutting sentences in half. Both values are configurable:

```bash
python ingest.py --chunk-tokens 700 --overlap 0.20
```

## Embeddings

Chunks are embedded with the official OpenAI embeddings endpoint. The default model is
`text-embedding-3-small` with 1536 dimensions, and both values can be overridden with
`EMBEDDING_MODEL` and `EMBEDDING_DIMENSIONS`. Texts are embedded in batches to keep
the number of requests low.

## Vector storage

Vectors are stored in a hosted Supabase project using the pgvector extension. The
schema lives in `data/supabase/schema.sql` and must be executed once in the Supabase
SQL editor. It creates:

- the `documents` table with `content`, `metadata` and a `vector(1536)` column;
- an approximate index for cosine distance;
- the `match_documents` function that returns the closest chunks with their metadata.

Every stored chunk carries source metadata: the source path, the original file name,
the chunk index and the estimated tokens of the chunk. Re-ingesting a document removes
its previous chunks first, so the index never contains duplicates.

## Retrieval at answer time

When the user sends a message, the question is embedded, the vector store returns the
top 5 chunks by cosine similarity, and chunks below the relevance threshold are
discarded. The surviving chunks are inserted into the system instructions together
with their source, so the model can cite the file it used.

If nothing is retrieved, or the score is below the threshold, the model is instructed
to say that there is not enough information in the knowledge base instead of inventing
content. The same rule applies when the retrieved context does not support the answer.

A retrieval failure never crashes the chat: the turn continues without context and a
`RAG warning` line explains what happened.

## Ingestion commands

```bash
# Embed and store every document in data/documents
python ingest.py

# Show the chunking result without calling any external service
python ingest.py --preview

# Clear the index first, then ingest everything again
python ingest.py --rebuild

# Ingest a single file
python ingest.py --only getting-started.md
```

## Testing the RAG flow

1. Run `python ingest.py` and check that every document reports `[ok]`.
2. Start the chat with `python main.py` and confirm that `/rag` reports the stored chunks.
3. Ask a question covered by a document and check that the `Sources:` line appears
   with a file name and a relevance score.
4. Ask about something outside the documents, for example the population of a city,
   and check that the answer states that there is not enough information in the
   knowledge base.
