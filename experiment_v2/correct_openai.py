import asyncio
import os
import random
import re
import sys
sys.path.insert(0, "..")
import pandas as pd
from corrector import Corrector
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

MODEL      = "gpt-4o-mini"
BATCH_SIZE = 10
INPUT_PATH  = "data/dataset_unificado_explode.parquet"
OUTPUT_PATH = "data/dataset_gpt4o_mini_corrections.parquet"
COL         = "corrections_gpt4o_mini"

corrector = Corrector(
    model=MODEL,
    base_url=os.getenv("OPENAI_BASE_URL") or None,
    api_key=os.getenv("OPENAI_API_KEY", ""),
    provider="openai",
    max_concurrency=10,
)


def make_python_clean(text: str) -> str:
    lines = text.splitlines()
    return "\n".join(l for l in lines if not l.strip().startswith("#")).strip()


def extract_retry_delay(err: str):
    m = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", err)
    if m:
        return int(m.group(1))
    m = re.search(r"retryDelay\":\"(\d+)s\"", err)
    return int(m.group(1)) if m else None


async def safe_execute(essay: str, theme: str) -> dict:
    for attempt in range(10):
        try:
            return await corrector.execute(essay_text=essay, essay_topic=theme)
        except Exception as e:
            delay = extract_retry_delay(str(e))
            wait = delay + random.uniform(1, 3) if delay else min(2 ** attempt + random.uniform(0, 1), 60)
            tqdm.write(f"[Retry {attempt + 1}] {e} | wait {wait:.1f}s")
            await asyncio.sleep(wait)
    raise RuntimeError("Falha após 10 tentativas")


async def run_corrections(df: pd.DataFrame) -> pd.DataFrame:
    if "output_python_clean" not in df.columns:
        df["output_python_clean"] = df["output"].apply(make_python_clean)

    if COL not in df.columns:
        df[COL] = None

    if os.path.exists(OUTPUT_PATH):
        df_saved = pd.read_parquet(OUTPUT_PATH)
        if COL in df_saved.columns:
            df[COL] = df_saved[COL]
        tqdm.write(f"Checkpoint carregado: {OUTPUT_PATH}")

    pending = df[df[COL].isna()].index.tolist()
    done = len(df) - len(pending)
    tqdm.write(f"Total: {len(df)} | Corrigidos: {done} | Pendentes: {len(pending)}")

    with tqdm(total=len(df), initial=done, unit="redação") as pbar:
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start : start + BATCH_SIZE]
            tasks = [
                safe_execute(df.at[i, "output_python_clean"], df.at[i, "theme"])
                for i in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in zip(batch, results):
                if isinstance(result, Exception):
                    tqdm.write(f"[{i}] ERRO FINAL: {result}")
                else:
                    df.at[i, COL] = {
                        k: result[k] for k in ("C1", "C2", "C3", "C4", "C5", "nota_final")
                    }
                pbar.update(1)

            df.to_parquet(OUTPUT_PATH, index=False)

    tqdm.write(f"Concluído. Salvo: {OUTPUT_PATH}")
    return df


if __name__ == "__main__":
    df = pd.read_parquet(INPUT_PATH)
    asyncio.run(run_corrections(df))
