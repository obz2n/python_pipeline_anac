# Pipeline ANAC - Extração, Carregamento e Transformação

Pipeline ELT automatizado para processar arquivos de dados da ANAC (Agência Nacional de Aviação Civil).

## Estrutura do Projeto

```
python_pipeline_anac/
├── docs/                 # Documentação do projeto
├── scripts/              # Scripts auxiliares
├── src/
│   ├── main.py           # Orquestração do pipeline
│   ├── extract.py        # Extração e conversão para Parquet
│   ├── load.py           # Carregamento em banco de dados
│   ├── config.py         # Configurações globais
│   └── __init__.py
├── data/
│   ├── raw/              # Arquivos TXT originais (ANAC)
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

**⚠️ IMPORTANTE:** Nunca commite o arquivo `.env` com dados reais! Ele está no `.gitignore`.

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

## Dependências

- **pandas**: Manipulação de dados
- **chardet**: Detecção de encoding
- **duckdb**: Leitura eficiente de Parquet
- **sqlalchemy**: ORM para banco de dados
- **pymysql**: Driver MySQL
- **dotenv**: Carregamento de variáveis de ambiente
- **loguru**: Sistema de logging avançado

Instale tudo com:
```bash
pip install pandas chardet duckdb sqlalchemy pymysql python-dotenv loguru
```

## Troubleshooting

### Erro: "Key PASSWORD not found in .env"
**Solução:** Crie arquivo `.env` com as credenciais:
```bash
cp .env.example .env
# Edite .env com suas credenciais
```

### Erro: "ValueError: Cannot parse retention from: '3'"
**Solução:** Use `retention=3` (inteiro) em vez de `retention="3"` (string)
- ✅ Já corrigido na versão atual

### Erro: "UnicodeDecodeError"
**Solução:** O pipeline testa múltiplos encodings automaticamente. Se falhar:
1. Verifique a encoding do arquivo original
2. Adicione a encoding em `config.py` em `ENCODINGS`

### Erro: "ConnectionError" ao conectar no BD
**Solução:**
1. Verifique se MySQL está rodando
2. Verifique credenciais em `.env`
3. Verifique host e porta (padrão: localhost:3306)

## Performance

- **Arquivos pequenos** (< 100MB): Rápido
- **Arquivos grandes** (> 1GB): Use `CHUNKSIZE` maior em `config.py`
- **Muitos arquivos**: Pipeline processa em sequência, considere paralelização futura

## Segurança

⚠️ **IMPORTANTE:**
- Nunca commite `.env` com credenciais reais
- Use variáveis de ambiente em produção
- Considere usar secrets management (AWS Secrets, HashiCorp Vault)
- Logs podem conter dados sensíveis - revise `logs/` regularmente

## Próximos Passos

- [ ] Criar camada de transformação com DBT
- [ ] Implementar deduplicação
- [ ] Adicionar testes unitários
- [ ] Documentação em SQL (views, procedures)
- [ ] Dashboard com métricas

## Suporte

Para dúvidas ou problemas, consulte os logs em `logs/anac.log`.

## Autor

[Juliano Laurentino](https://www.linkedin.com/in/julianolaurentinodasilva/)
