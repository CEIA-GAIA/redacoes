from agents.c1 import prompt as c1_prompt, C1Eval
from agents.c2 import prompt as c2_prompt, C2Eval
from agents.c3 import prompt as c3_prompt, C3Eval
from agents.c4 import prompt as c4_prompt, C4Eval
from agents.c5 import prompt as c5_prompt, C5Eval


c_agents = [
    (c1_prompt, C1Eval),
    (c2_prompt, C2Eval),
    (c3_prompt, C3Eval),
    (c4_prompt, C4Eval),
    (c5_prompt, C5Eval),
]

__include__ = [
    (c1_prompt, C1Eval),
    (c2_prompt, C2Eval),
    (c3_prompt, C3Eval),
    (c4_prompt, C4Eval),
    (c5_prompt, C5Eval),
    c_agents
]
