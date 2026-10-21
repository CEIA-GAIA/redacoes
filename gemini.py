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
DATA_PATH = "data/data/train-00000-of-00001.parquet"
OUTPUT_PATH = "data/redacoes_corrigidas_gemini_new_test.csv"
CHECKPOINT_PATH = "data/progresso_checkpoint.json"

corrector = Corrector(
    model="gemini-2.5-flash",
    base_url=None,
    api_key=API_KEY,
    provider="gemini",
    max_concurrency=2,
)

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

def is_enem_by_final_score(criterios):
    try:
        notas = [float(c["nota"]) for c in criterios]
        total = sum(notas)
        return (
            len(notas) == 5 and
            all(n in {0, 40, 80, 120, 160, 200} for n in notas) and
            0 <= total <= 1000
        )
    except:
        return False

def extract_human_scores(criterios):
    notas = [float(c["nota"]) for c in criterios]
    return {
        "hum_C1": notas[0],
        "hum_C2": notas[1],
        "hum_C3": notas[2],
        "hum_C4": notas[3],
        "hum_C5": notas[4],
        "hum_nota_final": sum(notas)
    }

def filter_enem_essays(df):
    df = df[
        df["correcaoes"].apply(
            lambda x: is_enem_by_final_score(
                x["Correção tradicional"]["criterios"]
            )
        )
    ].copy()

    human_scores = df["correcaoes"].apply(
        lambda x: extract_human_scores(
            x["Correção tradicional"]["criterios"]
        )
    )

    for col in ["hum_C1", "hum_C2", "hum_C3", "hum_C4", "hum_C5", "hum_nota_final"]:
        if col not in df.columns:
            df[col] = human_scores.apply(lambda x: x[col])

    return df

async def safe_execute(text, topic):
    for attempt in range(15):
        try:
            return await corrector.execute(
                essay_text=text,
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

def select_valid_themes(df):
    counts = df["tema"].value_counts()
    valid = counts[counts >= 100].index.tolist()
    return valid[:5]

async def main():
    df = pd.read_parquet(DATA_PATH)

    df = filter_enem_essays(df)

    selected_themes = select_valid_themes(df)

    df_filtered = df[df["tema"].isin(selected_themes)]

    samples = []
    remaining = 500

    for i, tema in enumerate(selected_themes):
        group = df_filtered[df_filtered["tema"] == tema]
        if i < len(selected_themes) - 1:
            n = min(len(group), remaining // (len(selected_themes) - i))
        else:
            n = remaining
        sampled = group.sample(n=n, random_state=42)
        samples.append(sampled)
        remaining -= n

    df_sample = pd.concat(samples).reset_index(drop=True)

    if os.path.exists(OUTPUT_PATH):
        df_saved = pd.read_csv(OUTPUT_PATH)
        df_sample.update(df_saved)

    for col in [
        "ia_C1", "ia_C2", "ia_C3", "ia_C4", "ia_C5", "ia_nota_final",
        "hum_C1", "hum_C2", "hum_C3", "hum_C4", "hum_C5", "hum_nota_final"
    ]:
        if col not in df_sample.columns:
            df_sample[col] = None

    checkpoint = load_checkpoint()
    start_idx = checkpoint["last_index"] + 1
    total = len(df_sample)

    for i in range(start_idx, total):
        row = df_sample.iloc[i]

        if df_sample.at[i, "ia_nota_final"] is not None:
            continue

        try:
            result = await safe_execute(row["text"], row["tema"])

            df_sample.at[i, "ia_C1"] = result["C1"]
            df_sample.at[i, "ia_C2"] = result["C2"]
            df_sample.at[i, "ia_C3"] = result["C3"]
            df_sample.at[i, "ia_C4"] = result["C4"]
            df_sample.at[i, "ia_C5"] = result["C5"]

            total_score = result["C1"] + result["C2"] + result["C3"] + result["C4"] + result["C5"]
            df_sample.at[i, "ia_nota_final"] = total_score

            save_checkpoint(i)

            if i % 5 == 0:
                df_sample.to_csv(OUTPUT_PATH, index=False)

            print(f"[{i+1}/{total}] OK | Nota: {total_score}")

            await asyncio.sleep(1.5)

        except Exception as e:
            print(f"[{i+1}/{total}] ERRO FINAL: {e}")
            await asyncio.sleep(5)

    print(df_sample.iloc[0])

    if df_sample["ia_nota_final"].isnull().any():
        raise ValueError("Existem redações não corrigidas")

    df_sample.to_csv(OUTPUT_PATH, index=False)

if __name__ == "__main__":
    asyncio.run(main())