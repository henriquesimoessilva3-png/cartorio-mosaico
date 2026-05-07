import hashlib
import hmac

from app.config import settings


def _digits_only(cpf_cnpj: str) -> str:
    return "".join(c for c in cpf_cnpj if c.isdigit())


def hash_cpf_cnpj(cpf_cnpj: str) -> str:
    cleaned = _digits_only(cpf_cnpj)
    if not cleaned:
        return ""
    return hmac.new(
        settings.secret_key.encode(),
        cleaned.encode(),
        hashlib.sha256,
    ).hexdigest()


def last_digit(cpf_cnpj: str) -> str:
    cleaned = _digits_only(cpf_cnpj)
    return cleaned[-1] if cleaned else ""
