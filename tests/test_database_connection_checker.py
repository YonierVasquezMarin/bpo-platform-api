from unittest.mock import MagicMock

from app.dtos.connection_status import ConnectionStatus
from app.services.database_connection_checker import DatabaseConnectionChecker


def test_database_checker_returns_ok_when_query_succeeds() -> None:
    engine = _build_engine()
    checker = DatabaseConnectionChecker(engine)

    result = checker.check_connection()

    assert result.name == "database"
    assert result.status == ConnectionStatus.OK
    assert result.message == "Conexión establecida"
    assert result.latency_ms is not None
    assert result.latency_ms >= 0
    engine.connect.assert_called_once()


def test_database_checker_returns_error_when_connect_fails() -> None:
    engine = MagicMock()
    engine.connect.side_effect = RuntimeError("login timeout expired")
    checker = DatabaseConnectionChecker(engine)

    result = checker.check_connection()

    assert result.name == "database"
    assert result.status == ConnectionStatus.ERROR
    assert result.message == "No se pudo establecer la conexión"
    assert result.latency_ms is not None


def _build_engine() -> MagicMock:
    connection = MagicMock()
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    return engine
