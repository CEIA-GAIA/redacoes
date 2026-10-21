import asyncio
import os
import random
import re
import sys

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from corrector import Corrector

load_dotenv()

INPUT_PATH = "experiment/data_cleaned.parquet"
OUTPUT_PATH = "experiment/data_corrected.parquet"
BATCH_SIZE = 10

corrector = Corrector(
    model="gemini-2.5-flash",
    base_url=None,
    api_key=os.getenv("GEMINI_API_KEY"),
    provider="gemini",
    max_concurrency=3,
)


def extract_retry_delay(error_str):
    match = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", error_str)
    if match:
        return int(match.group(1))
    match = re.search(r"retryDelay\":\"(\d+)s\"", error_str)
    if match:
        return int(match.group(1))
    return None


async def safe_execute(essay_text: str, topic: str) -> dict:
    for attempt in range(10):
        try:
            return await corrector.execute(essay_text=essay_text, essay_topic=topic)
        except Exception as e:
            err_str = str(e)
            retry_delay = extract_retry_delay(err_str)
            if retry_delay:
                wait = retry_delay + random.uniform(1, 3)
            else:
                wait = min(2**attempt + random.uniform(0, 1), 60)
            tqdm.write(f"[Retry {attempt + 1}] erro: {e} | aguardando {wait:.1f}s")
            await asyncio.sleep(wait)
    raise RuntimeError("Falha após 10 tentativas")


async def main():
    df = pd.read_parquet(INPUT_PATH)

    for col in ["ia_C1", "ia_C2", "ia_C3", "ia_C4", "ia_C5", "ia_nota_final"]:
        if col not in df.columns:
            df[col] = None

    if os.path.exists(OUTPUT_PATH):
        df_saved = pd.read_parquet(OUTPUT_PATH)
        for col in ["ia_C1", "ia_C2", "ia_C3", "ia_C4", "ia_C5", "ia_nota_final"]:
            if col in df_saved.columns:
                df[col] = df_saved[col]
        tqdm.write(f"Checkpoint carregado: {OUTPUT_PATH}")

    pending = df[df["ia_nota_final"].isna()].index.tolist()
    done = len(df) - len(pending)
    tqdm.write(f"Total: {len(df)} | Já corrigidos: {done} | Pendentes: {len(pending)}")

    with tqdm(total=len(df), initial=done, unit="redação") as pbar:
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch_indices = pending[batch_start : batch_start + BATCH_SIZE]

            tasks = [
                safe_execute(str(df.at[i, "outputs_clean"]), str(df.at[i, "problem"]))
                for i in batch_indices
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in zip(batch_indices, results):
                if isinstance(result, Exception):
                    tqdm.write(f"[{i}] ERRO FINAL: {result}")
                    pbar.update(1)
                    continue

                df.at[i, "ia_C1"] = result["C1"]
                df.at[i, "ia_C2"] = result["C2"]
                df.at[i, "ia_C3"] = result["C3"]
                df.at[i, "ia_C4"] = result["C4"]
                df.at[i, "ia_C5"] = result["C5"]
                df.at[i, "ia_nota_final"] = result["nota_final"]
                pbar.update(1)

            df.to_parquet(OUTPUT_PATH, index=False)

    tqdm.write(f"Concluído. Salvo: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
