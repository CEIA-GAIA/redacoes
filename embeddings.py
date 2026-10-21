import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import os

DATA_PATH = "/work/redacoes/data/data/train-00000-of-00001.parquet"
OUTPUT_PATH = "redacoes_com_bge_m3_embeddings.parquet"

# ----------------------------
# CUDA CHECK
# ----------------------------
if not torch.cuda.is_available():
    raise RuntimeError("CUDA NÃO disponível. Verifique GPU.")

device = torch.device("cuda")
print("✅ CUDA ativa:", torch.cuda.get_device_name(0))

model = SentenceTransformer("BAAI/bge-m3", device=device)

# ----------------------------
# LOAD DATA
# ----------------------------
df = pd.read_parquet(DATA_PATH)

def extract_fields(row):
    return {
        "titulo": row.get("titulo"),
        "tema": row.get("tema"),
        "texto": row.get("text")
    }

df_text = pd.DataFrame(df.apply(extract_fields, axis=1).tolist())

df_text["full_text"] = (
    "TÍTULO: " + df_text["titulo"].fillna("") + "\n"
    "TEMA: " + df_text["tema"].fillna("") + "\n"
    "REDAÇÃO:\n" + df_text["texto"].fillna("")
)

# ----------------------------
# RESUME MODE
# ----------------------------
if os.path.exists(OUTPUT_PATH):
    print("🔄 Arquivo existente detectado. Retomando progresso...")
    df_existing = pd.read_parquet(OUTPUT_PATH)

    df_text["embedding"] = None
    df_text.loc[:len(df_existing)-1, "embedding"] = df_existing["embedding"]
else:
    df_text["embedding"] = None

texts = df_text["full_text"].tolist()

# ----------------------------
# FIND START INDEX
# ----------------------------
if df_text["embedding"].notna().any():
    start_index = df_text["embedding"].last_valid_index() + 1
else:
    start_index = 0

print(f"▶️ Retomando a partir do índice {start_index}")

# ----------------------------
# PROCESS ONE BY ONE
# ----------------------------
for i in tqdm(range(start_index, len(texts)), desc="Gerando embeddings"):
    text = texts[i]

    embedding = model.encode(
        text,
        normalize_embeddings=True,
        show_progress_bar=False,
        device=device
    )

    # Store safely as list
    df_text.at[i, "embedding"] = embedding.tolist()

    # SAVE CHECKPOINT EVERY STEP
    df_text.to_parquet(OUTPUT_PATH)

print(f"✅ Finalizado. Arquivo salvo em: {OUTPUT_PATH}")
