import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI

from app.core.config import settings
from app.core.exceptions import DocumentIntelligenceNotConfiguredError, DocumentModelCallError

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Eres un analista de conocimiento de una operación BPO.
Interpretas un fragmento de un documento operativo para que un revisor humano decida si puede indexarse.
Responde únicamente con un objeto JSON.
Usa estas claves en inglés:
- interpretation: texto en español que explica el fragmento con fidelidad, sin inventar datos.
- structured_content: objeto con summary (string) y topics (lista de strings). summary y topics quedan en el idioma del fragmento.
- confidence: número entre 0 y 1. Usa un valor alto solo cuando el fragmento es claro, completo y accionable.
Si el fragmento está vacío, es ambiguo o no alcanza para operar, usa una confianza baja.
"""


@dataclass(frozen=True)
class ChunkInterpretationResult:
    interpretation: str
    structured_content: dict
    confidence: Decimal
    model_name: str
    prompt_version: str


class AzureChunkInterpretationClient:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        prompt_version: str,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._deployment = deployment
        self._prompt_version = prompt_version

    def interpret_chunk(self, content: str, section_title: str | None) -> ChunkInterpretationResult:
        self._ensure_configured()
        self._log_interpretation_call_started()
        raw_content = self._request_completion(content, section_title)
        try:
            result = self._build_result(raw_content)
        except (json.JSONDecodeError, InvalidOperation, KeyError, TypeError, ValueError):
            self._log_interpretation_response_unusable()
            return self._unreliable_result()
        self._log_interpretation_call_completed(result.confidence)
        return result

    def _ensure_configured(self) -> None:
        configuration_is_complete = bool(
            self._endpoint.strip() and self._api_key.strip() and self._deployment.strip()
        )
        if not configuration_is_complete:
            raise DocumentIntelligenceNotConfiguredError()

    def _request_completion(self, content: str, section_title: str | None) -> str:
        try:
            response = self._client().chat.completions.create(
                model=self._deployment,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_user_prompt(content, section_title)},
                ],
            )
        except (AuthenticationError, APIConnectionError, APIStatusError) as ex:
            self._log_interpretation_call_failed(ex)
            raise DocumentModelCallError("No se pudo consultar el modelo de interpretación") from ex
        if not response.choices:
            return ""
        return response.choices[0].message.content or ""

    def _build_user_prompt(self, content: str, section_title: str | None) -> str:
        title = section_title or "Sin sección"
        return f"Sección: {title}\n\nFragmento:\n{content}"

    def _build_result(self, raw_content: str) -> ChunkInterpretationResult:
        payload = self._load_payload(raw_content)
        interpretation = str(payload["interpretation"]).strip()
        if not interpretation:
            raise ValueError("La interpretación está vacía")
        return ChunkInterpretationResult(
            interpretation=interpretation,
            structured_content=self._structured_content(payload, interpretation),
            confidence=self._confidence(payload.get("confidence")),
            model_name=self._deployment,
            prompt_version=self._prompt_version,
        )

    def _load_payload(self, raw_content: str) -> dict:
        stripped = raw_content.strip()
        if stripped.startswith("```"):
            stripped = stripped.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            raise TypeError("La respuesta del modelo no es un objeto JSON")
        return payload

    def _structured_content(self, payload: dict, interpretation: str) -> dict:
        raw_structured = payload.get("structured_content")
        summary = interpretation
        topics: list[str] = []
        if isinstance(raw_structured, dict):
            raw_summary = raw_structured.get("summary")
            if isinstance(raw_summary, str) and raw_summary.strip():
                summary = raw_summary.strip()
            topics = self._topics(raw_structured.get("topics"))
        return {"summary": summary, "topics": topics}

    def _topics(self, raw_topics: object) -> list[str]:
        if not isinstance(raw_topics, list):
            return []
        return [str(topic).strip() for topic in raw_topics if str(topic).strip()]

    def _confidence(self, raw_confidence: object) -> Decimal:
        value = Decimal(str(raw_confidence))
        if value > 1:
            value = value / Decimal("100")
        if value < 0:
            value = Decimal("0")
        if value > 1:
            value = Decimal("1")
        return value.quantize(Decimal("0.01"))

    def _unreliable_result(self) -> ChunkInterpretationResult:
        interpretation = "No fue posible interpretar el fragmento de forma confiable."
        return ChunkInterpretationResult(
            interpretation=interpretation,
            structured_content={"summary": interpretation, "topics": []},
            confidence=Decimal("0.00"),
            model_name=self._deployment or "unavailable",
            prompt_version=self._prompt_version,
        )

    def _log_interpretation_call_started(self) -> None:
        logger.info(
            "Consultando el modelo de interpretación %s en %s",
            self._deployment,
            self._v1_base_url(),
        )

    def _log_interpretation_call_completed(self, confidence: Decimal) -> None:
        logger.info("El modelo %s respondió con confianza %s", self._deployment, confidence)

    def _log_interpretation_call_failed(self, error: Exception) -> None:
        logger.exception("Falló la llamada al modelo de interpretación %s: %s", self._deployment, error)

    def _log_interpretation_response_unusable(self) -> None:
        logger.warning("La respuesta del modelo %s no se pudo interpretar", self._deployment)

    def _client(self) -> OpenAI:
        return OpenAI(
            api_key=self._api_key,
            base_url=self._v1_base_url(),
            timeout=60,
        )

    def _v1_base_url(self) -> str:
        parsed = urlsplit(self._endpoint.strip())
        return f"{parsed.scheme}://{parsed.netloc}/openai/v1/"


def build_chunk_interpretation_client() -> AzureChunkInterpretationClient:
    return AzureChunkInterpretationClient(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        deployment=settings.azure_openai_chat_deployment,
        prompt_version=settings.interpretation_prompt_version,
    )
