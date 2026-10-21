import pandas as pd
import asyncio
import os
import json
import random
import re
from dotenv import load_dotenv
from corrector import Corrector

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "")
DATA_PATH = "rl/data/dataset_unificado_final.csv"  
OUTPUT_PATH = "rl/redacoes_corrigidas_gemini.csv"
CHECKPOINT_PATH = "rl/progresso_checkpoint.json"

corrector = Corrector(
    model="gemini-2.5-flash",
    base_url=None,
    api_key=API_KEY,
    provider="gemini",
    max_concurrency=2,
)

# =========================
# UTILS
# =========================

def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r") as f:
            return json.load(f)
    return {"last_index": -1}

def save_checkpoint(index):
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump({"last_index": index}, f)

def extract_retry_delay(error_str):
    match = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", error_str)
    if match:
        return int(match.group(1))
    match = re.search(r"retryDelay\":\"(\d+)s\"", error_str)
    if match:
        return int(match.group(1))
    return None

def exponential_backoff(attempt, base=2, max_wait=60):
    return min((base ** attempt) + random.uniform(0, 1), max_wait)

def preprocess_text(text, max_chars=6000):
    text = re.sub(r"\s+", " ", str(text))
    return text[:max_chars]

# =========================
# EXECUTION
# =========================

async def safe_execute(text, topic):
    for attempt in range(10):
        try:
            return await corrector.execute(
                essay_text=preprocess_text(text),
                essay_topic=topic
            )
        except Exception as e:
            err_str = str(e)

            retry_delay = extract_retry_delay(err_str)

            if retry_delay:
                wait_time = retry_delay + random.uniform(1, 3)
            elif "429" in err_str or "quota" in err_str.lower():
                wait_time = exponential_backoff(attempt)
            else:
                wait_time = exponential_backoff(attempt)

            print(f"Retry {attempt+1} | esperando {wait_time:.2f}s | erro: {e}")
            await asyncio.sleep(wait_time)

    raise RuntimeError("Falha após retries")

# =========================
# MAIN
# =========================

async def main():
    df = pd.read_csv(DATA_PATH)

    # renomeia para padronizar com pipeline antigo
    df = df.rename(columns={
        "essay": "text",
        "problem": "tema"
    })

    # garante coluna única de correção
    if "gemini_corrections" not in df.columns:
        df["gemini_corrections"] = None

    # retomar progresso
    if os.path.exists(OUTPUT_PATH):
        df_saved = pd.read_csv(OUTPUT_PATH)
        df.update(df_saved)

    checkpoint = load_checkpoint()
    start_idx = checkpoint["last_index"] + 1
    total = len(df)

    for i in range(start_idx, total):
        row = df.iloc[i]

        if pd.notnull(df.at[i, "gemini_corrections"]):
            continue

        try:
            result = await safe_execute(row["text"], row["tema"])

            total_score = (
                result["C1"] +
                result["C2"] +
                result["C3"] +
                result["C4"] +
                result["C5"]
            )

            # salva tudo em um único objeto JSON
            df.at[i, "gemini_corrections"] = json.dumps({
                "C1": result["C1"],
                "C2": result["C2"],
                "C3": result["C3"],
                "C4": result["C4"],
                "C5": result["C5"],
                "nota_final": total_score
            })

            save_checkpoint(i)

            if i % 5 == 0:
                df.to_csv(OUTPUT_PATH, index=False)

            print(f"[{i+1}/{total}] OK | Nota: {total_score}")

            await asyncio.sleep(1)

        except Exception as e:
            print(f"[{i+1}/{total}] ERRO FINAL: {e}")
            await asyncio.sleep(5)

    if df["gemini_corrections"].isnull().any():
        raise ValueError("Existem redações não corrigidas")

    df.to_csv(OUTPUT_PATH, index=False)

if __name__ == "__main__":
    asyncio.run(main())