# 🚀 Setup e Execução — ANAC Pipeline

## Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.12+ (para desenvolvimento local)
- PostgreSQL 16+ (incluído no docker-compose)

## 1. Configuração Inicial

### 1.1 Criar arquivo `.env`

```bash
cp .env.example .env
```

Edite `.env` com suas credenciais de banco de dados (padrão: `airflow/airflow`).

### 1.2 Iniciar os containers

```bash
docker compose up -d
```

**Aguarde 30-60 segundos** para que PostgreSQL, Airflow e Scheduler iniciem corretamente.

Verifique o status:
```bash
docker compose ps
```

## 2. Acessar Airflow UI

- URL: http://localhost:8080
- Usuário: `admin`
- Senha: `admin`

Navegue para **Admin → Connections** e verifique se `postgres_anac` está configurada corretamente.

## 3. Fluxo de Dados

```
DAG Ingestão (06:00)
    └─ verificar_arquivos
    └─ extract (CSV → Parquet)
    └─ load (Parquet → PostgreSQL:bronze)
    └─ trigger_dag_dbt
    
DAG dbt (08:00)
    └─ dbt_anac (TaskGroup)
         ├─ seed_aeroportos
         ├─ silver_voos
         └─ gold_* (3 modelos de agregação)
```

## 4. Preparar Dados

### Opção A: Carregar manualmente

1. Coloque arquivos CSV no diretório `./data/`
2. Acesse a DAG `dag_ingestao_anac` → **Trigger DAG** (botão play)
3. A execução rodará: extract → load → trigger_dbt

### Opção B: Schedule automático

- `dag_ingestao_anac`: **1º dia do mês às 06:00**
- `dag_dbt_anac`: **1º dia do mês às 08:00** (ou acionada manualmente)

## 5. Estrutura de Diretórios

```
python_pipeline_anac/
├── dags/                    # DAGs do Airflow
│   ├── dag_ingestao.py      # Ingestão CSV → Parquet → Bronze
│   └── dag_dbt.py           # Transformações Silver/Gold
├── dbt/                     # Projeto dbt
│   ├── dbt_project.yml
│   ├── profiles.yml         # (configurado automaticamente)
│   ├── models/
│   │   ├── bronze/          # Source + documentação
│   │   ├── silver/          # Limpeza e enriquecimento
│   │   └── gold/            # Agregações para BI
│   └── seeds/               # Dados de referência (aeroportos)
├── scripts/                 # Scripts de ETL (Python)
│   ├── extract.py           # Converte CSV → Parquet
│   └── load.py              # Carrega Parquet → PostgreSQL
├── data/                    # CSVs originais da ANAC
├── logs/                    # Logs do Airflow
├── docker-compose.yml       # Orquestração de containers
└── infra/docker/
    └── Dockerfile.airflow   # Imagem customizada com Cosmos + dbt
```

## 6. Troubleshooting

### "Connection postgres_anac not found"

Verifique em **Admin → Connections**. Se não existir, adicione manualmente:
- **Conn ID**: `postgres_anac`
- **Conn Type**: `Postgres`
- **Host**: `postgres`
- **Port**: `5432`
- **Login**: (valor de `$POSTGRES_USER`)
- **Password**: (valor de `$POSTGRES_PASSWORD`)
- **Schema**: `bronze`

### "DAG não aparece no Airflow"

1. Verifique se os arquivos `.py` estão em `./dags/`
2. Aguarde 5-10 segundos para que o Airflow rescaneie o diretório
3. Verifique erros: **Admin → Logs** ou `docker compose logs airflow-scheduler`

### "dbt: command not found"

Verifique se o Dockerfile foi reconstruído:
```bash
docker compose build --no-cache
docker compose up -d
```

### PostgreSQL não inicializa

Limpe o volume (⚠️ **CUIDADO: deleta todos os dados**):
```bash
docker compose down -v
docker compose up -d
```

## 7. Desenvolvimento Local (sem Docker)

Para testar scripts Python localmente:

```bash
# Criar ambiente virtual
python3.12 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Rodar extract manualmente
python scripts/extract.py

# Rodar load manualmente
python scripts/load.py
```

## 8. Monitoramento

### Ver logs em tempo real

```bash
docker compose logs -f airflow-scheduler
docker compose logs -f airflow-webserver
docker compose logs -f postgres
```

### Parar temporariamente (sem perder dados)

```bash
docker compose stop
```

### Limpar e reiniciar

```bash
docker compose down        # para tudo, mantém volumes
docker compose up -d       # reinicia
```

---

**Última atualização**: 2024
