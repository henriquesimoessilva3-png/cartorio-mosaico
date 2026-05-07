# Deploy gratuito — GitHub Pages + Render + Supabase

Guia pra subir o sistema completo sem custo recorrente. Rodando assim, o público acessa a app em `https://henriquesimoessilva3-png.github.io/cartorio-mosaico/` e ela conversa com um backend hospedado de graça.

**Limitações que você precisa aceitar:**
- Backend dorme após 15min sem requisições. Primeira request pós-sleep demora ~30s pra acordar (Render free tier).
- Postgres free Supabase: 500 MB de storage, sem garantias de SLA.
- Sem domínio próprio (URL é a `*.github.io` e `*.onrender.com`).
- Sem HTTPS customizado (usa o do Pages e do Render automaticamente).

Se isso não serve, vai pro `DEPLOY.md` (VPS Hetzner, €4/mês).

> **Aviso de segurança**: o frontend está com auto-login dev em `frontend/src/App.tsx` (constante `DEV_AUTOLOGIN`). Esse código vai pro browser do público — qualquer um com a URL pode ler as credenciais e logar. Ok pra demo com dado dummy; **antes de qualquer dado real, remova o auto-login e volte a tela de login**.

---

## Passo 1 — Postgres com PostGIS no Supabase

1. Crie conta em https://supabase.com (login com GitHub é mais rápido).
2. **New project**:
   - Name: `cartorio-mosaico-db`
   - Database password: gere uma forte e **anote** (você vai precisar)
   - Region: `South America (São Paulo)`
   - Pricing: Free
3. Espere ~2 min do provisionamento.
4. Vá em **Database** → **Extensions** → busque `postgis` → **Enable**.
5. Vá em **Settings** → **Database** → seção **Connection string**:
   - Copie a URL no formato URI
   - Substitua `[YOUR-PASSWORD]` pela senha do passo 2
   - Substitua o esquema `postgresql://` por `postgresql+psycopg://`
   - Resultado: `postgresql+psycopg://postgres.xxxx:SENHA@aws-0-sa-east-1.pooler.supabase.com:5432/postgres`
6. **Anote** — é o `DATABASE_URL` do próximo passo.

---

## Passo 2 — Backend no Render

1. Crie conta em https://render.com (login com GitHub).
2. **New +** → **Blueprint**.
3. **Connect a repository** → autorize → escolha `henriquesimoessilva3-png/cartorio-mosaico`.
4. Branch: `main` (a Blueprint lê `render.yaml` do repo).
5. **Apply**. Vai pedir envs:
   - `DATABASE_URL` → cola a URL do passo 1.5
   - `SECRET_KEY` → deixa "generate" marcado
   - `CORS_ORIGINS` → já preenchido com `https://henriquesimoessilva3-png.github.io`
6. Espere ~5 min do build inicial (Docker + alembic upgrade head).
7. Quando aparecer "Live", anote a URL (`https://cartorio-mosaico-api.onrender.com` ou similar).

### Bootstrap do admin

Banco novo está vazio. Cria o admin via shell do Render:

1. Dashboard Render → seu serviço → **Shell** (menu lateral).
2. Cole **com a senha que está em `frontend/src/App.tsx` na constante `DEV_AUTOLOGIN`**:
   ```bash
   python /app/scripts/create_admin.py "Henrique" \
     "$(grep -m1 email /app/../frontend/src/App.tsx | cut -d'"' -f2)" \
     "<copie-do-DEV_AUTOLOGIN>"
   ```
   Mais simples: abre `frontend/src/App.tsx` no GitHub web, copia os valores `email` e `password` dentro de `DEV_AUTOLOGIN`, e cola na linha:
   ```bash
   python /app/scripts/create_admin.py "Henrique" <email> <senha>
   ```

---

## Passo 3 — Configurar GitHub Pages com a URL do backend

1. **Settings** → **Secrets and variables** → **Actions** → aba **Variables** → **New repository variable**:
   - Name: `VITE_API_BASE`
   - Value: URL do passo 2.7 (ex.: `https://cartorio-mosaico-api.onrender.com`) **sem barra no final**
2. **Settings** → **Pages**:
   - Source: **GitHub Actions** (não "Deploy from a branch")

---

## Passo 4 — Disparar o deploy

Quando `feat: V0.5` for mergeado em `main`, o workflow `pages.yml` roda automaticamente:
- Build do frontend com `VITE_API_BASE` injetado
- Publica `frontend/dist` no Pages

Acompanhe em **Actions** → "Deploy frontend to GitHub Pages". Espera ~3 min.

Ao terminar, abra https://henriquesimoessilva3-png.github.io/cartorio-mosaico/ → auto-login → editor.

> **Primeira request demora 30s** porque o Render acordou. Não é bug.

---

## Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| `Failed to fetch /api/...` no console | `VITE_API_BASE` não foi setado, ou Pages usando build antigo | Confirma a Variable; refaz o deploy via "Re-run all jobs" |
| `CORS error` no console | `CORS_ORIGINS` no Render não bate com a origem real | No Render, edita env pra exatamente a origin do erro |
| Backend retorna 500 em `/api/*` | Migrations não rodaram | No Render Shell: `cd /app && alembic upgrade head` |
| Login auto-login falha | Admin não criado no banco novo, ou senha diferente | Roda `create_admin.py` no Render Shell com a senha do `DEV_AUTOLOGIN` |
| `permission denied to create extension "postgis"` | Banco Supabase sem PostGIS | Database → Extensions → enable postgis |
| Frontend vai mas mapa vazio | Backend dormindo (free tier) | Aguarda 30s, recarrega |

---

## Custos

- Pages: $0
- Render free: $0, **mas dorme**. $7/mês remove o sleep se virar produção.
- Supabase free: $0 até 500MB.

Total: **$0/mês** rodando como demo.
