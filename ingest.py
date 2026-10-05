"""Entry point for the knowledge-base ingestion pipeline."""

import sys

from chat_app.presentation.ingest_cli import main


if __name__ == "__main__":
    sys.exit(main())
