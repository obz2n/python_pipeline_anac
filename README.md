# Pipeline ANAC - Extração, Carregamento e Transformação

Pipeline ELT automatizado para processar arquivos de dados da ANAC (Agência Nacional de Aviação Civil).

![img](https://i.postimg.cc/XYggYxT1/Projeto-ANAC.png)

## Estrutura do Projeto

```
python_pipeline_anac/
├── dags/                      # DAGs do Airflow
│   ├── dag_ingestao.py        # Ingestão CSV → Parquet → Bronze
│   └── dag_dbt.py             # Transformações Silver/Gold com Cosmos
├── dbt/                       # Projeto dbt
│   ├── dbt_project.yml
│   ├── profiles.yml           # (configurado automaticamente)
│   ├── models/
│   │   ├── bronze/            # Source + documentação
│   │   ├── silver/            # Limpeza e enriquecimento
│   │   └── gold/              # Agregações para BI
│   └── seeds/                 # Dados de referência (aeroportos)
├── scripts/                   # Scripts de ETL (Python)
│   ├── extract.py             # Converte CSV → Parquet
│   └── load.py                # Carrega Parquet → PostgreSQL
├── data/                      # CSVs originais da ANAC
├── logs/                      # Logs do Airflow
├── docker/
│   └── Dockerfile.airflow     # Imagem customizada com Cosmos + dbt
├── docker-compose.yml         # Orquestração de containers
├── requirements.txt           # Dependências para desenvolvimento local
├── .env.example               # Exemplo de variáveis de ambiente
```

## Instalação

### Opção 1: Com Docker (Recomendado para Produção)

#### 1.1 Pré-requisitos
- Docker >= 20.10
- Docker Compose >= 2.0
- 4GB RAM mínimo

#### 1.2 Clonar o repositório
```bash
git clone <url-repositorio>
cd python_pipeline_anac
```

#### 1.3 Configurar variáveis de ambiente
```bash
cp .env.example .env
```

Edite `.env` com suas credenciais PostgreSQL:
```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua_senha_segura
POSTGRES_DB=postgres
POSTGRES_PORT=5433
```

#### 1.4 Iniciar containers
```bash
docker compose up -d
```

Aguarde 30-60 segundos para que os serviços iniciem:
```bash
docker compose ps
```

Todos os containers devem estar com status `Up` (health: healthy).

#### 1.5 Acessar Airflow UI
- **URL**: http://localhost:8080
- **Usuário**: `admin`
- **Senha**: `admin123`

Navegue para **Admin → Connections** e verifique se `postgres_anac` está configurada.

---

### Opção 2: Desenvolvimento Local (Sem Docker)

#### 2.1 Pré-requisitos
- Python 3.12+
- PostgreSQL 16+ instalado localmente

#### 2.2 Clonar o repositório
```bash
git clone <url-repositorio>
cd python_pipeline_anac
```

#### 2.3 Criar ambiente virtual
```bash
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

#### 2.4 Instalar dependências
```bash
pip install -r requirements.txt
```

#### 2.5 Configurar variáveis de ambiente
```bash
cp .env.example .env
```

Edite `.env` com suas credenciais PostgreSQL locais:
```ini
DB_USER=postgres
PASSWORD=sua_senha
HOST=localhost
PORT=5432
DATABASE=postgres
SCHEMA=bronze
DB_DIALECT=postgresql
```

#### 2.6 Rodar scripts Python manualmente

**Extract (CSV → Parquet):**
```bash
python scripts/extract.py
```

**Load (Parquet → PostgreSQL):**
```bash
python scripts/load.py
```

---

## Fluxo de Dados

```
┌─────────────────────────────────────────────────────────┐
│              DAG Ingestão (06:00)                        │
├─────────────────────────────────────────────────────────┤
│ 1. verificar_arquivos    (valida .csv/.parquet)         │
│ 2. extract               (CSV → Parquet)                │
│ 3. load                  (Parquet → Bronze)             │
│ 4. trigger_dag_dbt       (dispara transformações)       │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│              DAG dbt (08:00)                             │
├─────────────────────────────────────────────────────────┤
│ 1. seed_aeroportos       (carrega dados de referência)  │
│ 2. silver_voos           (limpeza + enriquecimento)     │
│ 3. gold_pontualidade     (agregações)                   │
│ 4. gold_volume_periodo   (agregações)                   │
│ 5. gold_ranking_rotas    (agregações)                   │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│              Schemas PostgreSQL                          │
├─────────────────────────────────────────────────────────┤
│ • bronze    (dados brutos, carregados)                  │
│ • silver    (dados limpos, enriquecidos)                │
│ • gold      (agregações prontas para BI)                │
└─────────────────────────────────────────────────────────┘
```

---

## Como Usar

### Com Airflow (Docker)

1. **Acessar UI**: http://localhost:8080

2. **Carregar dados manualmente** (primeira execução):
   - Coloque arquivos CSV em `./data/`
   - Acesse **DAGs → dag_ingestao_anac**
   - Clique no botão (Trigger DAG)
   - Monitore em **Graph** → **Tree View**

3. **Schedule automático**:
   - `dag_ingestao_anac`: 1º dia do mês às 06:00
   - `dag_dbt_anac`: 1º dia do mês às 08:00 (ou acionada automaticamente)

4. **Verificar logs**:
   ```bash
   docker compose logs -f airflow-scheduler
   docker compose logs -f airflow-webserver
   ```

### Desenvolvimento Local

```bash
# Extract manualmente
python scripts/extract.py

# Load manualmente
python scripts/load.py

# Rodar dbt manualmente
cd dbt
dbt run --select silver
dbt run --select gold
```

---

## Logs

### Com Docker
Os logs são armazenados em `./logs/` (volume montado):
```bash
# Ver logs em tempo real
docker compose logs -f airflow-webserver
docker compose logs -f airflow-scheduler
docker compose logs -f postgres
```

### Local
Logs são salvos em `logs/anac.log` com rotação automática:
- **Máximo**: 5MB por arquivo, mantém 3 backups
- **Nível**: INFO no console, DEBUG no arquivo
- **Colorido**: Mensagens no console são coloridas via `loguru`

### Exemplo de saída
```
2024-01-15 10:30:45 | INFO     | extract:processar_arquivos_txt:103 - Iniciando processamento de 5 arquivo(s)...
2024-01-15 10:30:46 | INFO     | extract:ler_arquivo_txt:48 - Lendo: voos_2023.txt
2024-01-15 10:30:46 | INFO     | extract:ler_arquivo_txt:56 - ✓ Lido com sucesso (125,430 linhas, 12 colunas)
2024-01-15 10:30:47 | INFO     | load:processar_carga:87 - Carregado em bronze.voos com sucesso
```

---

## Instalação de Dependências

### Arquivo `requirements.txt` (Desenvolvimento Local)
Contém todas as dependências para rodar scripts Python localmente:
- pandas, numpy
- dbt-core, dbt-postgres
- sqlalchemy, psycopg2
- duckdb, pyarrow
- chardet, loguru, python-dotenv
- apache-airflow (opcional)

**Instalação no Docker** (automática):
```bash
docker compose up -d
# O Dockerfile.airflow instala requirements-docker.txt automaticamente
```

**Instalação local**:
```bash
pip install -r requirements.txt
```

---

## Troubleshooting

### "Airflow webserver não responde" (ERR_SOCKET_NOT_CONNECTED)

1. Verificar se containers estão rodando:
   ```bash
   docker compose ps
   ```

2. Aguardar 30-60 segundos (inicialização lenta é normal)

3. Verificar logs:
   ```bash
   docker compose logs airflow-webserver --tail=50
   ```

4. Se persistir, reiniciar:
   ```bash
   docker compose restart airflow-webserver airflow-scheduler
   ```

### "Connection postgres_anac not found"

1. Acessar **Admin → Connections** em http://localhost:8080
2. Clique em `+` para criar nova conexão:
   - **Conn ID**: `postgres_anac`
   - **Conn Type**: `Postgres`
   - **Host**: `postgres`
   - **Port**: `5432`
   - **Login**: `${POSTGRES_USER}` (do `.env`)
   - **Password**: `${POSTGRES_PASSWORD}` (do `.env`)
   - **Schema**: `bronze`

### "DAGs não aparecem no Airflow"

1. Verificar se `.py` estão em `./dags/`
2. Aguardar 10 segundos (DAG rescan automático)
3. Recarregar navegador (F5)

### "dbt: command not found"

Reconstruir imagem Docker:
```bash
docker compose down
docker compose build --no-cache
docker compose up airflow-init
docker compose up -d
```

### "PostgreSQL não inicializa"

Limpar volumes (**deleta dados**):
```bash
docker compose down -v
docker compose up -d
```

---

## Segurança

**IMPORTANTE:**
- Nunca commite `.env` com credenciais reais
- Use variáveis de ambiente em produção
- Considere secrets management (AWS Secrets, HashiCorp Vault)
- Revise logs regularmente (podem conter dados sensíveis)
- Configure firewall para restringir acesso ao Airflow (8080)

---

## Backup e Recuperação

### Backup do PostgreSQL
```bash
docker compose exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql
```

### Restore do PostgreSQL
```bash
docker compose exec -T postgres psql -U $POSTGRES_USER $POSTGRES_DB < backup.sql
```

### Backup do Volume Docker
```bash
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

---

## Autor

[Juliano Laurentino](https://www.linkedin.com/in/julianolaurentinodasilva/)
