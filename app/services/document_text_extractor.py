import re
from io import BytesIO

from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

from app.core.exceptions import DocumentTextExtractionError, UnsupportedDocumentTypeError
from app.services.document_text import ExtractedSection

_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+)*)[.)]\s+(\S.*)$")
_TITLE_ENDING = set(".;:,")


class DocumentTextExtractor:
    def __init__(self) -> None:
        self._file_name = ""
        self._content = b""
        self._sections: list[ExtractedSection] = []
        self._current_title: str | None = None
        self._current_page: int | None = None
        self._current_lines: list[str] = []

    def extract(self, file_name: str, content: bytes) -> list[ExtractedSection]:
        self._file_name = file_name
        self._content = content
        self._reset_sections()
        try:
            return self._extract_by_extension()
        except (DocumentTextExtractionError, UnsupportedDocumentTypeError):
            raise
        except Exception as ex:
            raise DocumentTextExtractionError("No se pudo extraer el texto del documento") from ex

    def _reset_sections(self) -> None:
        self._sections = []
        self._current_title = None
        self._current_page = None
        self._current_lines = []

    def _extract_by_extension(self) -> list[ExtractedSection]:
        extension = self._file_name.lower().rsplit(".", maxsplit=1)[-1]
        if extension == "txt":
            return self._extract_plain_text()
        if extension == "docx":
            return self._extract_docx()
        if extension == "pdf":
            return self._extract_pdf()
        raise UnsupportedDocumentTypeError()

    def _extract_plain_text(self) -> list[ExtractedSection]:
        text = self._decode_text()
        self._consume_lines(text.splitlines(), page_number=None, detect_visual_titles=False)
        self._flush_section()
        return self._sections_or_raise("El archivo de texto no tiene contenido")

    def _extract_docx(self) -> list[ExtractedSection]:
        document = DocxDocument(BytesIO(self._content))
        self._current_page = None
        for block in self._iter_docx_blocks(document):
            self._consume_docx_block(block)
        self._flush_section()
        return self._sections_or_raise("El documento DOCX no tiene texto")

    def _extract_pdf(self) -> list[ExtractedSection]:
        reader = PdfReader(BytesIO(self._content))
        if not reader.pages:
            raise DocumentTextExtractionError("El PDF no contiene páginas")
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            self._consume_lines(page_text.splitlines(), page_number, detect_visual_titles=True)
        self._flush_section()
        return self._sections_or_raise("El PDF no contiene texto extraíble")

    def _decode_text(self) -> str:
        for encoding in ("utf-8-sig", "utf-8", "cp1252"):
            try:
                return self._content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise DocumentTextExtractionError("No se pudo leer el texto del archivo")

    def _consume_lines(self, lines: list[str], page_number: int | None, detect_visual_titles: bool) -> None:
        for line in lines:
            self._consume_line(line, page_number, detect_visual_titles)

    def _consume_line(self, line: str, page_number: int | None, detect_visual_titles: bool) -> None:
        stripped = line.strip()
        if not stripped:
            return
        if self._line_starts_section(stripped, detect_visual_titles):
            self._start_section(self._heading_title(stripped), page_number)
            return
        self._append_body_line(stripped, page_number)

    def _line_starts_section(self, line: str, detect_visual_titles: bool) -> bool:
        if _MARKDOWN_HEADING.match(line) or self._line_is_numbered_heading(line):
            return True
        if not detect_visual_titles:
            return False
        return self._line_looks_like_title(line)

    def _line_is_numbered_heading(self, line: str) -> bool:
        if not _NUMBERED_HEADING.match(line):
            return False
        line_is_short = len(line) <= 80
        line_does_not_end_as_sentence = line[-1] not in _TITLE_ENDING
        return line_is_short and line_does_not_end_as_sentence

    def _line_looks_like_title(self, line: str) -> bool:
        if len(line) < 4 or len(line) > 80:
            return False
        if line[-1] in _TITLE_ENDING:
            return False
        return len(line.split()) <= 8

    def _heading_title(self, line: str) -> str:
        markdown_match = _MARKDOWN_HEADING.match(line)
        if markdown_match:
            return markdown_match.group(1).strip()
        numbered_match = _NUMBERED_HEADING.match(line)
        if numbered_match and self._line_is_numbered_heading(line):
            return f"{numbered_match.group(1)} {numbered_match.group(2).strip()}"
        return line.strip()

    def _iter_docx_blocks(self, document: DocxDocument):
        for child in document.element.body.iterchildren():
            if child.tag == qn("w:p"):
                yield Paragraph(child, document)
            elif child.tag == qn("w:tbl"):
                yield Table(child, document)

    def _consume_docx_block(self, block: Paragraph | Table) -> None:
        if isinstance(block, Table):
            self._consume_docx_table(block)
            return
        text = block.text.strip()
        if not text:
            return
        if self._paragraph_is_heading(block):
            self._start_section(text, None)
            return
        self._append_body_line(text, None)

    def _consume_docx_table(self, table: Table) -> None:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                self._append_body_line(" | ".join(cells), None)

    def _paragraph_is_heading(self, paragraph: Paragraph) -> bool:
        style_name = ""
        if paragraph.style is not None and paragraph.style.name:
            style_name = paragraph.style.name
        return style_name.startswith("Heading") or style_name.startswith("Título") or style_name.startswith("Titulo")

    def _start_section(self, title: str, page_number: int | None) -> None:
        self._flush_section()
        self._current_title = title
        self._current_page = page_number
        self._current_lines = []

    def _append_body_line(self, line: str, page_number: int | None) -> None:
        if self._current_page is None:
            self._current_page = page_number
        self._current_lines.append(line)

    def _flush_section(self) -> None:
        text = "\n".join(self._current_lines).strip()
        if not text and self._current_title:
            text = self._current_title
        if text:
            self._sections.append(
                ExtractedSection(
                    title=self._current_title,
                    page_number=self._current_page,
                    text=text,
                )
            )
        self._current_title = None
        self._current_page = None
        self._current_lines = []

    def _sections_or_raise(self, message: str) -> list[ExtractedSection]:
        if not self._sections:
            raise DocumentTextExtractionError(message)
        return self._sections
