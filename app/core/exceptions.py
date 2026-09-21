class InvalidCredentialsError(Exception):
    def __init__(self) -> None:
        super().__init__("Credenciales inválidas")


class InactiveUserError(Exception):
    def __init__(self) -> None:
        super().__init__("El usuario está inactivo")
