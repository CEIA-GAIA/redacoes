#!/bin/bash
#SBATCH --partition=h100n2
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=24
#SBATCH --mem=180G
#SBATCH --ntasks=1
#SBATCH --time=UNLIMITED
#SBATCH --nodelist=dgx-H100-02
#SBATCH --job-name=Gaia-Searchs
#SBATCH --output=logs/gaia_embeddings_%j.out
#SBATCH --error=logs/gaia_embeddings_%j.err

CONTAINER_IMAGE="/home/user_lucasalves/images/vllm-openai_latest.sif"

mkdir -p logs

echo "Starting job on $(hostname)"
echo "Using container: $CONTAINER_IMAGE"

srun singularity exec  \
    --nv \
    --no-home \
    --bind "/home/user_lucasalves/projects/:/work" \
    --bind "/home/user_lucasalves/.local:/home/user_lucasalves/.local" \
    --bind "/home/user_lucasalves/.cache:/home/user_lucasalves/.cache" \
    "$CONTAINER_IMAGE" \
    bash -c "
        set -e
        pip install pandas
        cd /work/redacoes
        python3 embeddings.py
    "
