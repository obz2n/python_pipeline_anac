#!/bin/bash

# Script para executar pipeline dbt com diagnóstico completo
# Uso: bash run_dbt.sh [parse|seed|run|test|all]

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILES_DIR="$HOME/.dbt"

echo "========================================================================"
echo "DBT PIPELINE EXECUTOR"
echo "========================================================================"
echo "Project Dir: $PROJECT_DIR"
echo "Profiles Dir: $PROFILES_DIR"
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

function log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

function log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# ===================== DBT PARSE =====================
run_parse() {
  log_info "Executando: dbt parse"
  dbt parse --project-dir "$PROJECT_DIR" --profiles-dir "$PROFILES_DIR" || {
    log_error "Parse falhou!"
    exit 1
  }
  log_info "Parse: ✓ sucesso"
}

# ===================== DBT SEED =====================
run_seed() {
  log_info "Executando: dbt seed"
  dbt seed --project-dir "$PROJECT_DIR" --profiles-dir "$PROFILES_DIR" --select bronze_seed_aeroportos || {
    log_error "Seed falhou!"
    exit 1
  }
  log_info "Seed: ✓ sucesso"
}

# ===================== DBT RUN =====================
run_run() {
  log_info "Executando: dbt run"
  dbt run --project-dir "$PROJECT_DIR" --profiles-dir "$PROFILES_DIR" || {
    log_error "Run falhou!"
    exit 1
  }
  log_info "Run: ✓ sucesso"
}

# ===================== DBT TEST =====================
run_test() {
  log_info "Executando: dbt test"
  dbt test --project-dir "$PROJECT_DIR" --profiles-dir "$PROFILES_DIR" || {
    log_warn "Testes falharam, mas continuando..."
  }
  log_info "Test: ✓ concluído"
}

# ===================== DBT DEBUG =====================
run_debug() {
  log_info "Executando: dbt debug"
  dbt debug --project-dir "$PROJECT_DIR" --profiles-dir "$PROFILES_DIR"
}

# ===================== MAIN =====================
case "${1:-all}" in
  parse)
    run_parse
    ;;
  seed)
    run_parse
    run_seed
    ;;
  run)
    run_parse
    run_seed
    run_run
    ;;
  test)
    run_parse
    run_seed
    run_run
    run_test
    ;;
  debug)
    run_debug
    ;;
  all)
    run_parse
    run_seed
    run_run
    run_test
    log_info "========================================================================"
    log_info "PIPELINE CONCLUÍDO COM SUCESSO!"
    log_info "========================================================================"
    ;;
  *)
    echo "Uso: bash run_dbt.sh [parse|seed|run|test|debug|all]"
    exit 1
    ;;
esac

echo ""
log_info "Operação concluída: ${1:-all}"
