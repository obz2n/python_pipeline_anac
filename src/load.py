def processar_arquivos_txt(txt_files: list[str]) -> None:
    """
    Orquestra a leitura de todos os .txt e a conversão para .parquet.
    Arquivos com falha são registrados e ignorados sem interromper o processo.
    """
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    total = len(txt_files)
    sucessos = 0
    falhas = []

    print(f"\n{'=' * 60}")
    print(f"Iniciando processamento de {total} arquivo(s)...")
    print(f"{'=' * 60}")

    for i, file in enumerate(txt_files, start=1):
        file_path = pathlib.Path(file)
        print(f"\n[{i}/{total}]", end=" ")

        df = ler_arquivo_txt(file_path)

        if df is None:
            falhas.append(file_path.name)
            print(f"  IGNORADO: '{file_path.name}'")
            continue

        # Salvar como Parquet via Polars (mais eficiente que pandas.to_parquet)
        parquet_name = file_path.stem + ".parquet"
        parquet_path = OUTPUT_PATH / parquet_name

        try:
            pl.from_pandas(df).write_parquet(parquet_path)
            print(f"  Salvo em: {parquet_path}")
            sucessos += 1
        except Exception as e:
            print(f"  Erro ao salvar parquet '{parquet_name}': {e}")
            falhas.append(file_path.name)

    # Resumo final
    print(f"\n{'=' * 60}")
    print("Processamento concluído.")
    print(f"  Sucessos : {sucessos}/{total}")
    print(f"  Falhas   : {len(falhas)}/{total}")
    if falhas:
        print("Arquivos com falha:")
        for nome in falhas:
            print(f"    - {nome}")
    print(f"{'=' * 60}\n")
