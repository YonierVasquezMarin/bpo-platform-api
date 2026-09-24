import tiktoken

from app.services.document_text import PARAGRAPH_CONTENT_TYPE, ExtractedSection, TextChunkDraft

_SECTION_TITLE_MAX_LENGTH = 500


class TokenCounter:
    def __init__(self) -> None:
        self._encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self._encoding.encode(text))

    def split_text(self, text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
        tokens = self._encoding.encode(text)
        pieces: list[str] = []
        start = 0
        while start < len(tokens):
            window_end = min(start + max_tokens, len(tokens))
            piece, end = self._piece_within_limit(tokens, start, window_end, max_tokens)
            if piece:
                pieces.append(piece)
            if end >= len(tokens):
                break
            start = self._next_window_start(start, end, overlap_tokens)
        return pieces

    def _piece_within_limit(self, tokens: list[int], start: int, end: int, max_tokens: int) -> tuple[str, int]:
        piece = self._encoding.decode(tokens[start:end]).strip()
        while piece and self.count_tokens(piece) > max_tokens and end > start + 1:
            end -= 1
            piece = self._encoding.decode(tokens[start:end]).strip()
        return piece, end

    def _next_window_start(self, start: int, end: int, overlap_tokens: int) -> int:
        next_start = end - overlap_tokens
        if next_start <= start:
            return end
        return next_start


class ChunkSplitter:
    def __init__(self, token_counter: TokenCounter, max_tokens: int, overlap_tokens: int) -> None:
        self._token_counter = token_counter
        self._max_tokens = max_tokens
        self._overlap_tokens = overlap_tokens
        self._sections: list[ExtractedSection] = []
        self._drafts: list[TextChunkDraft] = []
        self._validate_window()

    def split(self, sections: list[ExtractedSection]) -> list[TextChunkDraft]:
        self._sections = sections
        self._drafts = []
        self._split_all_sections()
        return self._drafts

    def _validate_window(self) -> None:
        if self._max_tokens < 1:
            raise ValueError("CHUNK_MAX_TOKENS debe ser mayor que cero")
        if self._overlap_tokens < 0 or self._overlap_tokens >= self._max_tokens:
            raise ValueError("CHUNK_OVERLAP_TOKENS debe ser menor que CHUNK_MAX_TOKENS")

    def _split_all_sections(self) -> None:
        for section in self._sections:
            self._split_section(section)

    def _split_section(self, section: ExtractedSection) -> None:
        text = section.text.strip()
        if not text:
            return
        if self._token_counter.count_tokens(text) <= self._max_tokens:
            self._append_draft(section, text)
            return
        for piece in self._token_counter.split_text(text, self._max_tokens, self._overlap_tokens):
            self._append_draft(section, piece)

    def _append_draft(self, section: ExtractedSection, content: str) -> None:
        self._drafts.append(
            TextChunkDraft(
                chunk_number=len(self._drafts) + 1,
                content=content,
                section_title=self._trim_title(section.title),
                page_number=section.page_number,
                content_type=PARAGRAPH_CONTENT_TYPE,
                token_count=self._token_counter.count_tokens(content),
            )
        )

    def _trim_title(self, title: str | None) -> str | None:
        if title is None:
            return None
        stripped = title.strip()
        if not stripped:
            return None
        return stripped[:_SECTION_TITLE_MAX_LENGTH]
