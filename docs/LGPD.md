# LGPD — Tratamento de dados pessoais

## Bases legais aplicáveis

- **Art. 7º, II LGPD** — cumprimento de obrigação legal pelo controlador (cartório é delegatário de serviço público)
- **Art. 7º, III** — execução de políticas públicas
- **Art. 11, II "a"** — dados sensíveis se houver (raro em registro de imóveis)

## Dados tratados

| Dado | Sensibilidade | Tratamento |
|---|---|---|
| Nome do proprietário | Pessoal | Texto plano (público em matrícula) |
| CPF/CNPJ | Pessoal | **Hash SHA-256 + salt** + último dígito visível |
| Endereço do imóvel | Pessoal | Texto plano (público em matrícula) |
| Geometria do lote | Não pessoal | Plano |
| Confrontantes (nomes) | Pessoal indireto | Texto plano (público em matrícula) |

## Controles técnicos

- **Roles** com least-privilege: `admin`, `escrivao`, `escrevente`, `leitura`
- **Audit log** de toda ação (tabela `audit_log` com `payload_jsonb`)
- **Encriptação em repouso**:
  - V0/MVP: disco do servidor encriptado (FileVault/LUKS)
  - V1+: `pgcrypto` para colunas sensíveis se necessário
- **Encriptação em trânsito**: HTTPS obrigatório em produção
- **Senha**: bcrypt via `passlib`
- **JWT**: HS256 com `SECRET_KEY` em variável de ambiente; expiração curta

## Direitos do titular

Mesmo que o cartório opere sob delegação de serviço público:

- Acesso e correção: já são funções do próprio registro (Lei 6.015)
- Anonimização sob demanda: avaliar caso a caso (matrícula é pública por lei)

## Próximas ações

1. Documentar **base legal** explícita no Termo de Uso da ferramenta
2. Política de retenção de logs (audit_log) — sugestão: 5 anos
3. Política de backup off-site encriptado
4. Designar **encarregado** (DPO) — geralmente o titular do cartório
