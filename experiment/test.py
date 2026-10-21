import pandas as pd

df = pd.read_parquet("data_cleaned.parquet")

print("outputs_clean:", df.iloc[0]["outputs_clean"])
print("removed_parts:", df.iloc[0]["removed_parts"])