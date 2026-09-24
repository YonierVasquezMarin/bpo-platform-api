from dataclasses import dataclass


PARAGRAPH_CONTENT_TYPE = "PARAGRAPH"
PROCESSABLE_VERSION_STATUSES = {"UPLOADED", "FAILED", "APPROVED"}
HUMAN_CORRECTION_MODEL = "human-correction"
HUMAN_PROMPT_VERSION = "human-v1"


@dataclass(frozen=True)
class ExtractedSection:
    title: str | None
    page_number: int | None
    text: str


@dataclass(frozen=True)
class TextChunkDraft:
    chunk_number: int
    content: str
    section_title: str | None
    page_number: int | None
    content_type: str
    token_count: int
