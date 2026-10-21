import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

INPUT_PATH = "./themes/data.csv"
OUTPUT_PATH = "./themes/generated_essays.csv"
CHECKPOINT_PATH = "./themes/checkpoint.json"

df = pd.read_csv(INPUT_PATH)

if os.path.exists(OUTPUT_PATH):
    df_out = pd.read_csv(OUTPUT_PATH)
else:
    df_out = pd.DataFrame(columns=["problem", "essay_id", "essay"])

if os.path.exists(CHECKPOINT_PATH):
    with open(CHECKPOINT_PATH, "r") as f:
        checkpoint = json.load(f)
else:
    checkpoint = {"row": 0, "essay_id": 0}

def parse_output(text):
    start = text.find("<essay>")
    end = text.find("</essay>")
    if start != -1 and end != -1:
        return text[start + 7:end].strip()
    return text.strip()

for i in range(checkpoint["row"], len(df)):
    problem = df.loc[i, "problem"]

    for j in range(4):
        essay_id = checkpoint["essay_id"] + 1

        prompt = f"""
        Escreva uma redação dissertativa-argumentativa no estilo ENEM sobre o tema abaixo.

        Tema: {problem}

        A resposta deve conter apenas a redação entre as tags <essay></essay>.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        essay = parse_output(response.text)

        df_out = pd.concat([
            df_out,
            pd.DataFrame([{
                "problem": problem,
                "essay_id": essay_id,
                "essay": essay
            }])
        ], ignore_index=True)

        df_out.to_csv(OUTPUT_PATH, index=False)

        checkpoint["essay_id"] = essay_id
        with open(CHECKPOINT_PATH, "w") as f:
            json.dump(checkpoint, f)

        time.sleep(1)

    checkpoint["row"] = i + 1
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(checkpoint, f)
