"""Source e-Protocolo (estado do PR / Arpen) — STUB.

Aguardando definições do cliente:
- Tipo de certificado: A1 PFX vs A3 PKCS#11.
- Endpoint WSDL/REST (Arpen-PR? Arpen-SP? extrajudicial.org?).
- Formato de retorno (XML padrão CRI ou JSON?).
- Rate-limit oficial.
- Credenciais (login/senha do cartório? token?).

Quando essas dúvidas estiverem resolvidas, implementar `iter_records` análogo
a `CsvSource.iter_records()` produzindo `MatriculaCreate`.
"""
from __future__ import annotations

from collections.abc import Iterable

from app.schemas.matricula import MatriculaCreate


class EProtocoloSource:
    def __init__(
        self,
        cert_path: str | None = None,
        usuario: str | None = None,
        senha: str | None = None,
        ambiente: str = "homologacao",
    ) -> None:
        self.cert_path = cert_path
        self.usuario = usuario
        self.senha = senha
        self.ambiente = ambiente

    def iter_records(self) -> Iterable[MatriculaCreate]:
        raise NotImplementedError(
            "EProtocoloSource: aguardando credenciais e WSDL — ver issue #N"
        )
