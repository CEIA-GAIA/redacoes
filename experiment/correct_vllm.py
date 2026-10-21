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

VLLM_BASE_URL = "http://10.100.0.121:8222/v1"
VLLM_API_KEY = "vllm_ceia_100"
MODEL = "google/gemma-4-31B-it"
MODEL_SLUG = MODEL.replace("/", "_")

INPUT_PATH = "data_python_clean_openai_gpt-4o-mini.parquet"
OUTPUT_PATH = f"data_vllm_{MODEL_SLUG}.parquet"
BATCH_SIZE = 5

corrector = Corrector(
    model=MODEL,
    base_url=VLLM_BASE_URL,
    api_key=VLLM_API_KEY,
    provider="vllm",
    extra_body={"chat_template_kwargs": {"enable_thinking": True}},
    max_concurrency=5,
)


def extract_retry_delay(error_str: str):
    m = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", error_str)
    if m:
        return int(m.group(1))
    m = re.search(r"retryDelay\":\"(\d+)s\"", error_str)
    if m:
        return int(m.group(1))
    return None


async def safe_execute(essay_text: str, topic: str) -> dict:
    for attempt in range(10):
        try:
            return await corrector.execute(essay_text=essay_text, essay_topic=topic)
        except Exception as e:
            err_str = str(e)
            delay = extract_retry_delay(err_str)
            wait = (
                delay + random.uniform(1, 3)
                if delay
                else min(2**attempt + random.uniform(0, 1), 60)
            )
            tqdm.write(f"[Retry {attempt + 1}] erro: {e} | aguardando {wait:.1f}s")
            await asyncio.sleep(wait)
    raise RuntimeError("Falha apos 10 tentativas")


async def main():
    df = pd.read_parquet(INPUT_PATH)
    tqdm.write(f"Loaded {len(df)} rows from {INPUT_PATH}")
    tqdm.write(f"Model: {MODEL}  |  Endpoint: {VLLM_BASE_URL}")

    corrector_cols = [
        "ia_vllm_C1",
        "ia_vllm_C2",
        "ia_vllm_C3",
        "ia_vllm_C4",
        "ia_vllm_C5",
        "ia_vllm_nota_final",
    ]
    for col in corrector_cols:
        if col not in df.columns:
            df[col] = None

    if os.path.exists(OUTPUT_PATH):
        df_saved = pd.read_parquet(OUTPUT_PATH)
        for col in corrector_cols:
            if col in df_saved.columns:
                df[col] = df_saved[col]
        tqdm.write(f"Checkpoint carregado: {OUTPUT_PATH}")

    pending = df[df["ia_vllm_nota_final"].isna()].index.tolist()
    done = len(df) - len(pending)
    tqdm.write(f"Total: {len(df)} | Corrigidos: {done} | Pendentes: {len(pending)}")

    with tqdm(total=len(df), initial=done, unit="redacao") as pbar:
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch_idx = pending[batch_start : batch_start + BATCH_SIZE]
            tasks = [
                safe_execute(
                    str(df.at[i, "outputs"]),
                    str(df.at[i, "problem"]),
                )
                for i in batch_idx
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in zip(batch_idx, results):
                if isinstance(result, Exception):
                    tqdm.write(f"[{i}] ERRO FINAL: {result}")
                    pbar.update(1)
                    continue
                df.at[i, "ia_vllm_C1"] = result["C1"]
                df.at[i, "ia_vllm_C2"] = result["C2"]
                df.at[i, "ia_vllm_C3"] = result["C3"]
                df.at[i, "ia_vllm_C4"] = result["C4"]
                df.at[i, "ia_vllm_C5"] = result["C5"]
                df.at[i, "ia_vllm_nota_final"] = result["nota_final"]
                pbar.update(1)

            df.to_parquet(OUTPUT_PATH, index=False)

    tqdm.write(f"\nConcluido. Salvo: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
