#!/usr/bin/env python3
"""
Script de diagnóstico para verificar carregamento de .env
Execute da raiz do projeto: python debug_env.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

print("=" * 70)
print("DIAGNÓSTICO - CARREGAMENTO DE .env")
print("=" * 70)

# Verificar arquivo .env
env_path = Path(__file__).parent / ".env"
print(f"\n1. Procurando .env em: {env_path}")
print(f"   Arquivo existe? {env_path.exists()}")

if not env_path.exists():
    print("\n❌ ERRO: Arquivo .env não encontrado!")
    print("   Solução: cp .env.example .env")
    exit(1)

# Carregar .env
print(f"\n2. Carregando variáveis de: {env_path}")
load_dotenv(dotenv_path=env_path)

# Ler valores
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DATABASE = os.getenv("DATABASE")

print(f"\n3. Variáveis de ambiente lidas:")
print(f"   USER     = {USER or '(não definido)'}")
print(f"   PASSWORD = {'*' * len(PASSWORD) if PASSWORD else '(não definido)'}")
print(f"   HOST     = {HOST or '(não definido)'}")
print(f"   PORT     = {PORT or '(não definido)'}")
print(f"   DATABASE = {DATABASE or '(não definido)'}")

# Verificar se estão corretos
print(f"\n4. Validação de variáveis:")
errors = []

if not USER:
    errors.append("   ❌ USER não está definido")
if not PASSWORD:
    errors.append("   ❌ PASSWORD não está definido")
if not HOST:
    errors.append("   ❌ HOST não está definido")
if not DATABASE:
    errors.append("   ❌ DATABASE não está definido")

if errors:
    print("\n   Problemas encontrados:")
    for error in errors:
        print(error)
    print("\n   Edite .env e verifique as variáveis")
    exit(1)
else:
    print("   ✓ Todas as variáveis estão definidas corretamente!")

# Testar conexão
print(f"\n5. Testando conexão com MariaDB/MySQL...")
print(f"   URL: mysql+pymysql://{USER}:***@{HOST}:{PORT or '3306'}/{DATABASE}")

try:
    import sqlalchemy

    port_str = f":{PORT}" if PORT else ":3306"
    connection_string = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}{port_str}/{DATABASE}"
    engine = sqlalchemy.create_engine(connection_string)
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("SELECT 1"))
        print(f"   ✓ Conexão estabelecida com sucesso!")
except Exception as e:
    print(f"   ❌ Erro ao conectar: {e}")
    print(f"\n   🔍 Dicas de diagnóstico:")
    print(f"   1. MariaDB está rodando? `docker ps`")
    print(f"   2. HOST={HOST} está correto?")
    print(f"   3. PORT={PORT or '3306'} está correto?")
    print(f"   4. USER={USER} existe no MariaDB?")
    print(f"   5. PASSWORD está correta?")
    print(f"   6. DATABASE {DATABASE} existe?")
    print(f"\n   Para Docker, tente:")
    print(f"   docker exec -it <container_id> mysql -u {USER} -p")
    exit(1)

print("\n" + "=" * 70)
print("✓ DIAGNÓSTICO CONCLUÍDO COM SUCESSO!")
print("=" * 70)
print("\nVocê pode executar: python src/main.py")
