# Pipeline ANAC - Extração, Carregamento e Transformação

Pipeline ELT automatizado para processar arquivos de dados da ANAC (Agência Nacional de Aviação Civil).

![img](https://i.postimg.cc/XYggYxT1/Projeto-ANAC.png)

## Estrutura do Projeto

```
python_pipeline_anac/
├── dbt/                  # Modelos DBT para transformação
├── docs/                 # Documentação do projeto
├── scripts/              # Scripts auxiliares
├── src/
│   ├── main.py           # Orquestração do pipeline
│   ├── extract.py        # Extração e conversão para Parquet
│   ├── load.py           # Carregamento em banco de dados
│   ├── config.py         # Configurações globais
│   └── __init__.py
├── data/
│   ├── bronze/              # Arquivos TXT originais (ANAC)
│   └── processed/        # Arquivos Parquet processados
├── logs/                 # Arquivos de log
├── .env                  # Variáveis de ambiente (não commitar)
├── requirements.txt      # Dependências Python
└── README.md            # Este arquivo
```

## Instalação

### 1. Clonar o repositório
```bash
git clone <url-repositorio>
cd python_pipeline_anac
```

### 2. Criar ambiente virtual
```bash
python3.12 -m venv .anac
source .anac/bin/activate  # Linux/Mac
# ou
.anac\Scripts\activate  # Windows
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Copie `.env.example` para `.env`:
```bash
cp .env.example .env
```

Edite `.env` com suas credenciais:
```ini
USER=root
PASSWORD=sua_senha_mysql
HOST=localhost
PORT=PORTA  
DATABASE=seu_db
```

**IMPORTANTE:** Nunca commite o arquivo `.env` com dados reais! Ele está no `.gitignore`.

## Uso

### Executar o pipeline completo
```bash
python src/main.py
```

O pipeline executa automaticamente 3 etapas:

#### Etapa 1: Extração (TXT → Parquet)
- Lê arquivos `.txt` da pasta `data/raw/`
- Detecta encoding automaticamente (chardet)
- Converte para Parquet em `data/processed/`
- Suporta fallback de encodings para arquivos problemáticos

#### Etapa 2: Validação
- Carrega Parquets com DuckDB
- Valida integridade dos dados
- Exibe estatísticas (linhas, colunas)

#### Etapa 3: Carregamento em BD (Opcional)
- Carrega Parquets em MySQL usando SQLAlchemy
- Requer credenciais configuradas em `.env`
- Se `.env` não estiver configurado, a etapa é pulada graciosamente

## Logs

Os logs são salvos em `logs/anac.log` com rotação automática:
- **Arquivo**: máximo 5MB por arquivo, mantém 3 backups
- **Console**: mensagens INFO em tempo real (coloridas)
- **Arquivo**: mensagens DEBUG para debugging profundo

### Exemplos de saída
```
2024-01-15 10:30:45 | INFO     | main:main:58 - Etapa 1: Extração de dados (txt -> parquet)
2024-01-15 10:30:45 | INFO     | extract:processar_arquivos_txt:103 - Iniciando processamento de 5 arquivo(s)...
2024-01-15 10:30:46 | INFO     | extract:ler_arquivo_txt:48 - Lendo: voos_2023.txt
2024-01-15 10:30:46 | INFO     | extract:ler_arquivo_txt:56 - ✓ Lido com sucesso (125,430 linhas, 12 colunas)
```

## Tratamento de Erros

O pipeline é robusto e continua processando mesmo com falhas:

- **Falha em um arquivo TXT**: Etapa 1 continua com próximos arquivos
- **Falha ao salvar Parquet**: Arquivo é marcado como falho, pipeline continua
- **Falta de credenciais BD**: Etapa 3 é pulada com aviso, Etapas 1 e 2 continuam
- **Erro de conexão BD**: Etapa 3 interrompida, mas Etapas 1 e 2 já completadas

Todos os erros são registrados em `logs/anac.log`.

## Configurações Avançadas

### `config.py`
```python
DATA_RAW_PATH = Path("python_pipeline_anac/data/raw")
DATA_PROCESSED_PATH = Path("python_pipeline_anac/data/processed")
CHUNKSIZE = 50_000  # Linhas por batch no INSERT
ENCODINGS = [...]   # Fallback de encodings a testar
```

### Limitar carregamento em BD
```python
# Em load.py, função carregar_raw()
stats_load = carregar_raw(engine, limite=3)  # Carrega apenas 3 arquivos
```

## Performance

- **Arquivos pequenos** (< 100MB): Rápido
- **Arquivos grandes** (> 1GB): Use `CHUNKSIZE` maior em `config.py`
- **Muitos arquivos**: Pipeline processa em sequência, considere paralelização futura

## Segurança

**IMPORTANTE:**
- Nunca commite `.env` com credenciais reais
- Use variáveis de ambiente em produção
- Considere usar secrets management (AWS Secrets, HashiCorp Vault)
- Logs podem conter dados sensíveis - revise `logs/` regularmente

## Suporte

Para dúvidas ou problemas, consulte os logs em `logs/anac.log`.

## Autor

[Juliano Laurentino](https://www.linkedin.com/in/julianolaurentinodasilva/)
