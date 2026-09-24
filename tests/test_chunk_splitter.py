from app.services.chunk_splitter import ChunkSplitter, TokenCounter
from app.services.document_text import PARAGRAPH_CONTENT_TYPE, ExtractedSection


def test_splitter_keeps_each_short_section_as_one_chunk() -> None:
    sections = [
        ExtractedSection(title="Politica de pagos", page_number=1, text="El pago se realiza en cinco dias."),
        ExtractedSection(title="Excepciones", page_number=2, text="No aplica a proveedores internacionales."),
    ]

    drafts = ChunkSplitter(TokenCounter(), max_tokens=800, overlap_tokens=80).split(sections)

    assert [draft.chunk_number for draft in drafts] == [1, 2]
    assert drafts[0].section_title == "Politica de pagos"
    assert drafts[0].page_number == 1
    assert drafts[0].content_type == PARAGRAPH_CONTENT_TYPE
    assert drafts[1].section_title == "Excepciones"
    assert drafts[0].token_count > 0


def test_splitter_breaks_a_long_section_and_keeps_the_title() -> None:
    sections = [ExtractedSection(title="Anexo largo", page_number=3, text="palabra " * 2000)]

    drafts = ChunkSplitter(TokenCounter(), max_tokens=50, overlap_tokens=10).split(sections)

    assert len(drafts) > 1
    assert all(draft.section_title == "Anexo largo" for draft in drafts)
    assert all(draft.page_number == 3 for draft in drafts)
    assert [draft.chunk_number for draft in drafts] == list(range(1, len(drafts) + 1))
    assert all(draft.token_count <= 50 for draft in drafts)
