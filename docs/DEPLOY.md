# Deploy em VPS

Guia para subir o sistema completo (Postgres+PostGIS, backend FastAPI, frontend React) num único servidor barato. Estimativa de custo: **€4-6/mês** (Hetzner CX22) ou **US$ 6/mês** (DigitalOcean Basic).

## Pré-requisitos

- Servidor Linux (Ubuntu 22.04 ou 24.04 recomendado)
- 2 vCPU, 4 GB RAM, 40 GB SSD (suficiente para um cartório com até ~50k matrículas)
- Domínio próprio (opcional mas recomendado para HTTPS)
- Acesso root via SSH

## Passo 1 — Provisionar VPS

### Hetzner Cloud (recomendado por preço/qualidade)

1. Crie conta em https://hetzner.com/cloud
2. **Add Server** → CX22 (Ubuntu 24.04, AMD), datacenter Helsinki ou Falkenstein.
3. Adicione sua chave SSH na criação.
4. Custo: ~€4,51/mês.

### DigitalOcean

1. **Create Droplet** → Basic → Regular CPU → 2GB / 1 CPU / 50GB.
2. Ubuntu 24.04 LTS, região São Paulo (NYC se não tiver).
3. Custo: ~US$ 12/mês.

## Passo 2 — Setup inicial do servidor

```bash
# Conecte via SSH
ssh root@SEU_IP

# Atualize tudo
apt update && apt upgrade -y

# Instale Docker + Compose plugin
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin git ufw

# Firewall: só SSH + HTTP + HTTPS
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Cria usuário não-root para o app (boa prática)
adduser --disabled-password --gecos "" cartorio
usermod -aG docker cartorio
su - cartorio
```

## Passo 3 — Clone e configure

```bash
# Como usuário cartorio
cd ~
git clone https://github.com/henriquesimoessilva3-png/cartorio-mosaico.git
cd cartorio-mosaico

# Gere segredos fortes
cp .env.prod.example .env.prod
nano .env.prod
# Preencha:
#   SECRET_KEY=$(openssl rand -hex 32)
#   POSTGRES_PASSWORD=$(openssl rand -hex 16)
```

## Passo 4 — Build e suba

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml build
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d

# Verifique
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
```

Em poucos segundos:
- Postgres+PostGIS rodando com as extensões habilitadas pela primeira migration
- Backend em `localhost:8000` (interno)
- Frontend em `localhost:80` (público) servido pelo Nginx, proxy `/api` → backend

Acesse `http://SEU_IP` para ver a tela de login.

## Passo 5 — Crie o primeiro admin

```bash
docker compose -f docker-compose.prod.yml exec backend \
    python /app/scripts/create_admin.py "Henrique" henrique@exemplo.com sua-senha-12345
```

Faça login na URL acima com esse usuário. Depois crie escrivães e leitura via `/api/auth/register` (UI ainda não tem essa tela; use `curl` ou Swagger em `http://SEU_IP/api/docs`).

## Passo 6 — HTTPS com Caddy (recomendado)

Apontar um domínio para o IP do servidor (registro A) e adicionar Caddy como reverse-proxy:

```bash
# Em ~/cartorio-mosaico, crie Caddyfile:
cat > Caddyfile << 'EOF'
cartorio.exemplo.com.br {
    reverse_proxy frontend:80
}
EOF
```

Adicione um serviço Caddy no `docker-compose.prod.yml`:

```yaml
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - frontend
```

E remova o mapping `80:80` do serviço `frontend` (passa a só expor internamente).

Caddy emite e renova certificados Let's Encrypt automaticamente.

## Passo 7 — Backup

Configure cron diário no servidor:

```bash
# crontab -e
0 3 * * * /home/cartorio/cartorio-mosaico/scripts/backup.sh
```

Crie `scripts/backup.sh` (não está no repo — adicione localmente):

```bash
#!/bin/bash
set -e
DEST=/home/cartorio/backups
mkdir -p "$DEST"
docker compose -f /home/cartorio/cartorio-mosaico/docker-compose.prod.yml exec -T postgres \
    pg_dump -U postgres cartorio_mosaico | gzip > "$DEST/db-$(date +%F).sql.gz"
# Mantém últimos 30 dias
find "$DEST" -name "db-*.sql.gz" -mtime +30 -delete
```

Para off-site, sincronize `/home/cartorio/backups` com S3 / Backblaze B2 via `rclone`.

## Passo 8 — Atualizar versões

```bash
cd ~/cartorio-mosaico
git pull
docker compose --env-file .env.prod -f docker-compose.prod.yml build
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
# Migrations aplicam sozinhas no startup do backend
```

## Monitoramento mínimo

```bash
# Status dos containers
docker compose -f docker-compose.prod.yml ps

# Tail logs
docker compose -f docker-compose.prod.yml logs -f --tail=100

# Uso de disco
df -h
docker system df

# Limpa imagens antigas mensalmente
docker system prune -af
```

## Troubleshooting

**Backend não sobe / erro de conexão com postgres.**
Postgres pode levar ~10s pra ficar pronto. O `depends_on: condition: service_healthy` resolve, mas se editou o compose pode ter perdido. Rode `docker compose logs postgres` para confirmar.

**Frontend mostra 502 ao chamar API.**
O nginx tenta resolver o nome `backend` — só funciona dentro da rede Docker. Confirme que o serviço backend está `Up`. Se renomeou, ajuste `proxy_pass` em `frontend/nginx.conf`.

**Memorial PDF dá 500.**
Provavelmente faltam libs nativas no container. O Dockerfile já instala `libpango-1.0-0 libpangoft2-1.0-0 libcairo2` — se editou, confira.

**LGPD: dados em trânsito.**
HTTPS é obrigatório em produção (Lei 13.709/2018, Art. 46). Use Caddy do passo 6 — sem HTTPS, dados de proprietários trafegam em claro.

## Custo total estimado

- VPS Hetzner CX22: €4,51/mês
- Domínio .com.br: ~R$ 40/ano
- Backups (Backblaze B2 ~10GB): US$ 0,06/mês
- **Total**: ~R$ 35/mês

Capacidade aproximada do CX22:
- ~50k matrículas + lotes versionados
- ~10 usuários simultâneos confortáveis
- Quando passar disso: subir para CX32 (€7,55/mês, 4 vCPU, 8 GB)
