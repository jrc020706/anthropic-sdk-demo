from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    api_key: str
    base_url: Optional[str]
    model: str