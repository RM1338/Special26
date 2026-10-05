"""Claim and ClaimSet (05 §2, 08 §2.1)."""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    org = "org"
    scheme = "scheme"
    sender_email = "sender_email"
    reply_to = "reply_to"
    url = "url"
    phone = "phone"
    upi_id = "upi_id"
    amount = "amount"
    hr_person = "hr_person"
    address = "address"
    role = "role"
    stipend = "stipend"
    deadline = "deadline"
    process = "process"
    legal_id = "legal_id"
    image = "image"


Source = Literal["regex", "dictionary", "legal_line", "pattern", "display_name", "eml_header", "llm", "user"]


class Claim(BaseModel):
    id: str                                  # "c_" + 8 hex, stable within a check
    type: ClaimType
    value: dict
    raw: str
    span: tuple[int, int] | None = None   # char offsets in redacted text
    source: Source
    confidence: float = Field(ge=0, le=1)

    @staticmethod
    def make(type: ClaimType, value: dict, raw: str, source: Source, confidence: float,
             span: tuple[int, int] | None = None) -> Claim:
        """Deterministic id from type, raw and span, so re-extraction gives the same ids."""
        h = hashlib.sha256(f"{type.value}|{raw}|{span}".encode()).hexdigest()[:8]
        return Claim(id=f"c_{h}", type=type, value=value, raw=raw, span=span, source=source, confidence=confidence)


class ClaimSet(BaseModel):
    claims: list[Claim]
    warnings: list[str] = []

    def first(self, t: ClaimType) -> Claim | None:
        return next((c for c in self.claims if c.type == t), None)

    def all(self, t: ClaimType) -> list[Claim]:
        return [c for c in self.claims if c.type == t]

    @property
    def org_name(self) -> str | None:
        c = self.first(ClaimType.org)
        return c.value.get("name") if c else None

    @property
    def process(self) -> dict:
        c = self.first(ClaimType.process)
        return c.value if c else {}
