import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.crypto import build_password_cipher_from_settings


def main() -> None:
    try:
        execute_cli()
    except Exception as ex:
        registrar_log_error_al_procesar_texto(ex)
        sys.exit(1)


def execute_cli() -> None:
    arguments = parse_arguments()
    cipher = build_password_cipher_from_settings()
    if action_is_encrypt(arguments.action):
        print_encrypted_text(cipher.encrypt_password(arguments.text))
        return
    print_decrypted_text(cipher.decrypt_password(arguments.text))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cifra o descifra contraseñas con ENCRYPTION_KEY y ENCRYPTION_SALT de .env"
    )
    parser.add_argument(
        "action",
        choices=["encrypt", "decrypt"],
        help="Acción a ejecutar",
    )
    parser.add_argument(
        "text",
        help="Texto plano a cifrar o texto cifrado a descifrar",
    )
    return parser.parse_args()


def action_is_encrypt(action: str) -> bool:
    return action == "encrypt"


def print_encrypted_text(encrypted_text: str) -> None:
    print("Texto cifrado:")
    print(encrypted_text)


def print_decrypted_text(decrypted_text: str) -> None:
    print("Texto descifrado:")
    print(decrypted_text)


def registrar_log_error_al_procesar_texto(ex: Exception) -> None:
    print(f"Error al procesar el texto: {ex}", file=sys.stderr)


if __name__ == "__main__":
    main()
