import pandas as pd
import os

subsets = [
    'step_10', 'step_20', 'step_60', 'step_50',
    'step_76', 'step_30', 'step_40', 'step_70',
    'gemma-3-4b-it'
]

dfs = []

for subset in subsets:
    path = os.path.join(
        "data",
        subset,
        "train-00000-of-00001.parquet"
    )
    
    df = pd.read_parquet(path)
    df["subset"] = subset 
    
    dfs.append(df)

df_final = pd.concat(dfs, ignore_index=True)

output_path = "data/dataset_unificado.parquet"
df_final.to_parquet(output_path, index=False)

print("Arquivo final salvo em:", output_path)
