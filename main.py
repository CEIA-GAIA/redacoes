import os
import time
import json
import random
import re
import pandas as pd
from openai import OpenAI
from agents import c_agents
from dotenv import load_dotenv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://10.100.0.112:1111/v1")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "api_key")
VLLM_MODEL = os.getenv("VLLM_MODEL", "openai/gpt-oss-120b")

client = OpenAI(
    api_key=VLLM_API_KEY,
    base_url=VLLM_BASE_URL
)

DATA_PATH = "/work/redacoes/data/data/train-00000-of-00001.parquet"
OUTPUT_PARQUET = f"data/redacoes_com_correcao_{VLLM_MODEL.replace('/', '_')}.parquet"

MAX_RETRIES = 5
BASE_BACKOFF = 1.3
MAX_ESSAYS_TO_PROCESS = 30000
SAVE_EVERY = 10
MAX_WORKERS = min(16, (os.cpu_count() or 8) * 2)

REQUIRED_COLS = [
    "ia_C1", "ia_C2", "ia_C3", "ia_C4", "ia_C5",
    "ia_nota_final",
    "hum_C1", "hum_C2", "hum_C3", "hum_C4", "hum_C5",
    "hum_nota_final",
    "ia_reasoning"
]


def ensure_columns(df):
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def extract_human_scores(row):
    criterios = row["correcaoes"]["Correção tradicional"]["criterios"]
    scores = {f"C{i}": None for i in range(1, 6)}
    for c in criterios:
        criterio = c["criterio"]
        nota = int(c["nota"])
        if criterio.endswith(("1", "2", "3", "4", "5")):
            scores[f"C{criterio[-1]}"] = nota
    scores["nota_final"] = int(row["correcaoes"]["Correção tradicional"]["nota_final"])
    return scores


def extract_json_safe(text: str):
    try:
        return json.loads(text)
    except:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"JSON inválido:\n{text}")


def call_gpt_oss(prompt, response_format):
    base_system_prompt = (
        "Você DEVE responder SOMENTE com JSON válido. "
        "NÃO inclua texto extra. "
        "Siga exatamente o schema."
    )

    for attempt in range(MAX_RETRIES):
        completion = client.chat.completions.create(
            model=VLLM_MODEL,
            messages=[
                {"role": "system", "content": base_system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.15,
            top_p=0.9,
            reasoning_effort="high"
        )

        message = completion.choices[0].message
        raw_text = message.content.strip()
        reasoning_text = getattr(message, "reasoning_content", None)

        try:
            parsed_json = extract_json_safe(raw_text)
            validated = response_format(**parsed_json)
            result = validated.dict()
            result["_reasoning"] = reasoning_text
            return result
        except Exception as e:
            print(f"Tentativa {attempt + 1} falhou: {e}")

    raise ValueError("Falha após múltiplas tentativas")


def ask_gpt_evaluate_structured(essay_text: str, essay_topic: str):
    result = {}
    reasoning_log = {}

    for c_prompt, c_eval in c_agents:
        prompt = c_prompt.format(essay_text=essay_text, essay_topic=essay_topic)

        for attempt in range(MAX_RETRIES):
            try:
                eval_result = call_gpt_oss(prompt, c_eval)
                reasoning_log[c_eval.__name__] = eval_result.pop("_reasoning", None)
                result.update(eval_result)
                break
            except Exception as e:
                print(f"Tentativa {attempt + 1} falhou: {e}")
        else:
            raise RuntimeError("Falha persistente no provider")

    result["_full_reasoning"] = reasoning_log
    return result


def process_row(idx, row):
    if pd.notna(row.get("ia_nota_final")):
        return idx, None

    text = row["text"]
    topic = row["tema"]

    result = ask_gpt_evaluate_structured(text, topic)
    scores = extract_human_scores(row)

    return idx, {
        "ia_C1": result["C1"],
        "ia_C2": result["C2"],
        "ia_C3": result["C3"],
        "ia_C4": result["C4"],
        "ia_C5": result["C5"],
        "ia_nota_final": sum(result[f"C{i}"] for i in range(1, 6)),
        "hum_C1": scores["C1"],
        "hum_C2": scores["C2"],
        "hum_C3": scores["C3"],
        "hum_C4": scores["C4"],
        "hum_C5": scores["C5"],
        "hum_nota_final": scores["nota_final"],
        "ia_reasoning": json.dumps(result["_full_reasoning"], ensure_ascii=False)
    }


if __name__ == "__main__":
    base_df = pd.read_parquet(DATA_PATH).head(MAX_ESSAYS_TO_PROCESS)
    base_df = ensure_columns(base_df)

    if os.path.exists(OUTPUT_PARQUET):
        saved_df = pd.read_parquet(OUTPUT_PARQUET)
        saved_df = ensure_columns(saved_df)
        df = base_df.combine_first(saved_df)
    else:
        df = base_df.copy()

    df = ensure_columns(df)

    pending = df[df["ia_nota_final"].isna()]

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_row, idx, row): idx
            for idx, row in pending.iterrows()
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing essays"):
            idx = futures[future]
            try:
                row_idx, res = future.result()
                if res:
                    results.append((row_idx, res))
            except:
                pass

            if len(results) >= SAVE_EVERY:
                for r_idx, res in results:
                    for key, value in res.items():
                        df.at[r_idx, key] = value
                df.to_parquet(OUTPUT_PARQUET, index=False)
                results.clear()

    for r_idx, res in results:
        for key, value in res.items():
            df.at[r_idx, key] = value

    df.to_parquet(OUTPUT_PARQUET, index=False)

    print(df.columns.tolist())
    print(df.head())
