"""Source CRI eletrônico — STUB.

Aguardando definições do cliente:
- Provedor (ONR, eRegister, outro?).
- Forma de autenticação (cert digital, OAuth, login/senha).
- Endpoint REST oficial.
- Schema do JSON de retorno.

Quando resolvido, implementar `iter_records` produzindo `MatriculaCreate`.
"""
from __future__ import annotations

from collections.abc import Iterable

from app.schemas.matricula import MatriculaCreate


class CriEletronicoSource:
    def __init__(
        self,
        provedor: str = "onr",
        token: str | None = None,
    ) -> None:
        self.provedor = provedor
        self.token = token

    def iter_records(self) -> Iterable[MatriculaCreate]:
        raise NotImplementedError(
            "CriEletronicoSource: aguardando provedor + credenciais — ver issue #N"
        )
