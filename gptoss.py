import pandas as pd
import asyncio
import os
import json
import random
import re
from corrector import Corrector

DATA_PATH = "rl/themes/generated_essays.csv"
OUTPUT_PATH = "rl/redacoes_corrigidas_gpt_oss.csv"
CHECKPOINT_PATH = "rl/progresso_checkpoint.json"

VLLM_BASE_URL = "http://localhost:1111/v1"
API_KEY = "api_key"
MODEL = "openai/gpt-oss-120b"

corrector = Corrector(
    model=MODEL,
    base_url=VLLM_BASE_URL,
    api_key=API_KEY,
    provider="openai",
    max_concurrency=5
)

def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r") as f:
            return json.load(f)
    return {"last_index": -1}

def save_checkpoint(index):
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump({"last_index": index}, f)

def exponential_backoff(attempt, base=2, max_wait=60):
    return min((base ** attempt) + random.uniform(0, 1), max_wait)

async def safe_execute(text, topic):
    for attempt in range(15):
        try:
            return await corrector.execute(
                essay_text=text,
                essay_topic=topic
            )
        except Exception as e:
            wait_time = exponential_backoff(attempt)
            print(f"Retry {attempt+1} | esperando {wait_time:.2f}s | erro: {e}")
            await asyncio.sleep(wait_time)
    raise RuntimeError("Falha após retries")

async def main():
    df = pd.read_csv(DATA_PATH)

    if os.path.exists(OUTPUT_PATH):
        df_saved = pd.read_csv(OUTPUT_PATH)
        df.update(df_saved)

    for col in [
        "ia_C1", "ia_C2", "ia_C3", "ia_C4", "ia_C5", "ia_nota_final"
    ]:
        if col not in df.columns:
            df[col] = None

    checkpoint = load_checkpoint()
    start_idx = checkpoint["last_index"] + 1
    total = len(df)

    for i in range(start_idx, total):
        row = df.iloc[i]

        if pd.notna(df.at[i, "ia_nota_final"]):
            continue

        try:
            result = await safe_execute(row["essay"], row["problem"])

            df.at[i, "ia_C1"] = result["C1"]
            df.at[i, "ia_C2"] = result["C2"]
            df.at[i, "ia_C3"] = result["C3"]
            df.at[i, "ia_C4"] = result["C4"]
            df.at[i, "ia_C5"] = result["C5"]

            total_score = result["C1"] + result["C2"] + result["C3"] + result["C4"] + result["C5"]
            df.at[i, "ia_nota_final"] = total_score

            save_checkpoint(i)

            if i % 5 == 0:
                df.to_csv(OUTPUT_PATH, index=False)

            print(f"[{i+1}/{total}] OK | Nota: {total_score}")

            await asyncio.sleep(1.5)

        except Exception as e:
            print(f"[{i+1}/{total}] ERRO FINAL: {e}")
            await asyncio.sleep(5)

    if df["ia_nota_final"].isnull().any():
        raise ValueError("Existem redações não corrigidas")

    df.to_csv(OUTPUT_PATH, index=False)

if __name__ == "__main__":
    asyncio.run(main())