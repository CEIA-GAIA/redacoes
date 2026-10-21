#!/bin/bash
#SBATCH --partition=h100n2
#SBATCH --gres=gpu:h100:0
#SBATCH --cpus-per-task=8
#SBATCH --mem=30G
#SBATCH --ntasks=1
#SBATCH --time=UNLIMITED
#SBATCH --nodelist=dgx-H100-02
#SBATCH --job-name=VLLM-DATASET-GAIA

PORT=$1
if [ -z "${PORT}" ]; then
    PORT=1111
fi

export CONTAINER_IMAGE="/home/user_lucasalves/images/gaia-redacoes-experiment.sif"

srun singularity exec \
    --nvccli \
    --env PORT=${PORT} \
    --bind "/home/user_lucasalves/projects/:/work/" \
    "${CONTAINER_IMAGE}" \
    bash -c '
        cd /work/redacoes/experiment_v2
        python3 correct_openai.py
    '

