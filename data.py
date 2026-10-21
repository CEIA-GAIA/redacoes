from huggingface_hub import hf_hub_download

local_path = hf_hub_download(
    repo_id="CEIA-UFG/redacoes",    
    repo_type="dataset",               
    local_dir="data",
    filename="data/train-00000-of-00001.parquet",
    local_dir_use_symlinks=False        
)

print("Arquivo salvo em:", local_path)
