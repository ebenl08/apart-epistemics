# Sourced by m6_run.sh and by hand. Copy to /root/m6env.sh on a new pod.
source /root/envs/clm-env/bin/activate
R=/workspace/apart-epistemics
export PYTHONPATH=$R/context-language-models/clm:$R/infra:$R/infra/semantic_entropy
export OPENAI_API_KEY=EMPTY
cd $R
L=runs/m5-lmlog
C="python3 infra/semantic_entropy/collect.py"
