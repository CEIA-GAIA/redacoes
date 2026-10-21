import asyncio
import json
import os
import random
import re

import google.generativeai as genai
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel
from tqdm import tqdm

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
_model = genai.GenerativeModel("gemini-2.5-flash")

SEMAPHORE = asyncio.Semaphore(3)
OUTPUT_PATH = "data_cleaned.parquet"
BATCH_SIZE = 10

SYSTEM_PROMPT = (
    "Você é um especialista em redações do ENEM. "
    "O texto abaixo pode conter a redação misturada com títulos markdown, observações, "
    "comentários do corretor, notas, rubricas ou outros elementos que NÃO fazem parte da redação em si. "
    "Sua tarefa:\n"
    "1. Extraia SOMENTE o corpo da redação (parágrafos escritos pelo aluno).\n"
    "2. Remova comentários de correção, observações e qualquer texto que não seja da redação.\n"
    "Responda SOMENTE com JSON válido no formato:\n"
    '{"essay": "<texto limpo da redação>", "removed_parts": ["<trecho removido 1>", "<trecho removido 2>"]}\n'
    "Se nada foi removido, use array vazio em removed_parts."
)


class EssayCleanup(BaseModel):
    essay: str
    removed_parts: list[str]


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"JSON inválido:\n{text[:300]}")


async def clean_essay(essay_text: str) -> EssayCleanup:
    async with SEMAPHORE:
        for attempt in range(10):
            try:
                response = await asyncio.to_thread(
                    _model.generate_content,
                    f"{SYSTEM_PROMPT}\n\nTexto:\n{essay_text}",
                )
                parsed = _extract_json(response.text)
                return EssayCleanup(**parsed)
            except Exception as e:
                wait = min(2**attempt + random.uniform(0, 1), 60)
                tqdm.write(f"[Retry {attempt + 1}] erro: {e} | aguardando {wait:.1f}s")
                await asyncio.sleep(wait)
        raise RuntimeError("Falha após 10 tentativas")


async def main():
    df = pd.read_parquet("data_expanded.parquet")

    # Inicializa colunas de saída se não existirem
    if "outputs_clean" not in df.columns:
        df["outputs_clean"] = None
    if "removed_parts" not in df.columns:
        df["removed_parts"] = None

    # Retoma progresso anterior
    if os.path.exists(OUTPUT_PATH):
        df_saved = pd.read_parquet(OUTPUT_PATH)
        for col in ["outputs_clean", "removed_parts"]:
            if col in df_saved.columns:
                df[col] = df_saved[col]
        tqdm.write(f"Checkpoint carregado: {OUTPUT_PATH}")

    pending = df[df["outputs_clean"].isna()].index.tolist()
    done = len(df) - len(pending)
    tqdm.write(f"Total: {len(df)} | Já processados: {done} | Pendentes: {len(pending)}")

    with tqdm(total=len(df), initial=done, unit="redação") as pbar:
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch_indices = pending[batch_start : batch_start + BATCH_SIZE]

            tasks = [clean_essay(str(df.at[i, "outputs"])) for i in batch_indices]
            results = await asyncio.gather(*tasks)

            for i, result in zip(batch_indices, results):
                df.at[i, "outputs_clean"] = result.essay
                df.at[i, "removed_parts"] = result.removed_parts
                pbar.update(1)

            df.to_parquet(OUTPUT_PATH, index=False)

    removed_count = df["removed_parts"].apply(lambda x: len(x) > 0 if isinstance(x, list) else False).sum()
    tqdm.write(f"Concluído. Salvo: {OUTPUT_PATH}")
    tqdm.write(f"Redações com conteúdo removido: {removed_count}/{len(df)}")


if __name__ == "__main__":
    asyncio.run(main())
