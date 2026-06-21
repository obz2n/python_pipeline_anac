# Quick Start - Pipeline ANAC

Comece em 5 minutos! 🚀

## Pré-requisitos

- Python 3.12+
- MySQL rodando (ou remova Etapa 3 temporariamente)
- Git

## Passos

### 1️⃣ Setup inicial (2 min)
```bash
# Clonar/Entrar no projeto
cd python_pipeline_anac

# Criar virtual env
python3.12 -m venv .anac
source .anac/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements.txt
```

### 2️⃣ Configurar banco de dados (1 min)
```bash
# Copiar exemplo
cp .env.example .env

# Editar .env com suas credenciais
nano .env
```

Exemplo de `.env`:
```ini
USER=root
PASSWORD=sua_senha
HOST=localhost
DATABASE=anac_db
```

### 3️⃣ Preparar dados (1 min)
Coloque seus arquivos `.txt` em:
```
data/raw/
```

### 4️⃣ Executar pipeline (1 min)
```bash
python src/main.py
```

## Pronto! ✅

O pipeline vai:
1. 📥 **Ler** arquivos TXT
2. 🔄 **Converter** para Parquet
3. ✔️ **Validar** com DuckDB
4. 💾 **Carregar** em MySQL (se configurado)

Confira os logs em `logs/anac.log`

## Erros comuns?

| Erro | Solução |
|------|---------|
| `.env` não existe | `cp .env.example .env` |
| Password não configurado | Edite `.env` |
| MySQL offline | Inicie MySQL |
| Sem arquivos TXT | Coloque em `data/raw/` |

## Próxima etapa?

Leia [README.md](README.md) para documentação completa.
