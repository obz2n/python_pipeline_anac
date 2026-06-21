#!/usr/bin/env python3
"""
Script para monitorar uso de memória durante o pipeline
Executa o pipeline e mostra picos de memória em tempo real
"""

import subprocess
import threading
import time
from pathlib import Path

import psutil

# ============================================================
# Monitorar memória em thread separada
# ============================================================

memory_stats = {
    "peak_mb": 0,
    "peak_percent": 0.0,
    "readings": [],
}


def monitor_memory():
    """Thread que monitora memória a cada 100ms"""
    while monitor_memory.running:
        try:
            mem = psutil.virtual_memory()
            memory_stats["peak_mb"] = max(
                memory_stats["peak_mb"], mem.used / (1024 * 1024)
            )
            memory_stats["peak_percent"] = max(
                memory_stats["peak_percent"], mem.percent
            )
            memory_stats["readings"].append(
                {
                    "time": time.time(),
                    "used_mb": mem.used / (1024 * 1024),
                    "percent": mem.percent,
                }
            )
        except:
            pass
        time.sleep(0.1)


# ============================================================
# Executar pipeline
# ============================================================

print("=" * 70)
print("MONITORANDO USO DE MEMÓRIA - PIPELINE ANAC")
print("=" * 70)
print(f"Limite de segurança: 8000 MB (8 GB)")
print()

monitor_memory.running = True
monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
monitor_thread.start()

start_time = time.time()

try:
    # Executar pipeline
    result = subprocess.run(
        ["python", "src/main.py"],
        cwd="/home/casal-inked/Documentos/wokspace/python_pipeline_anac",
        capture_output=False,
    )
    exit_code = result.returncode
except Exception as e:
    print(f"Erro ao executar pipeline: {e}")
    exit_code = 1
finally:
    monitor_memory.running = False
    monitor_thread.join()

elapsed = time.time() - start_time

# ============================================================
# Relatório de memória
# ============================================================

print()
print("=" * 70)
print("RELATÓRIO DE MEMÓRIA")
print("=" * 70)
print(f"Tempo total: {elapsed:.1f} segundos")
print(
    f"Pico de memória: {memory_stats['peak_mb']:.0f} MB ({memory_stats['peak_percent']:.1f}%)"
)
print(f"Limite seguro: 8000 MB")

if memory_stats["peak_mb"] > 8000:
    print(f"⚠️  AVISO: Pico acima de 8 GB! ({memory_stats['peak_mb']:.0f} MB)")
else:
    print(f"✓ Memória dentro do limite seguro")

# Estatísticas adicionais
if memory_stats["readings"]:
    readings = memory_stats["readings"]
    avg_mb = sum(r["used_mb"] for r in readings) / len(readings)
    min_mb = min(r["used_mb"] for r in readings)
    max_mb = max(r["used_mb"] for r in readings)

    print()
    print(f"Memória mínima: {min_mb:.0f} MB")
    print(f"Memória média:  {avg_mb:.0f} MB")
    print(f"Memória máxima: {max_mb:.0f} MB")

print()
print(f"Exit code: {exit_code}")
print("=" * 70)
