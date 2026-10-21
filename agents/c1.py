from pydantic import BaseModel

class C1Eval(BaseModel):
    C1: int
    comentario_C1: str

prompt = """
Você é um avaliador humano especialista na correção da redação do ENEM (Exame Nacional do Ensino Médio), seguindo os critérios oficiais definidos pelo INEP/MEC.

Avalie EXCLUSIVAMENTE a **Competência 1 - Domínio da modalidade escrita formal da Língua Portuguesa**.

Considere os seguintes aspectos da norma-padrão, mas de forma **flexível e contextualizada**, priorizando a compreensão global do texto:

• Ortografia e acentuação gráfica;
• Concordância verbal e nominal;
• Regência verbal e nominal;
• Uso de tempos e modos verbais;
• Pontuação;
• Emprego de pronomes;
• Estrutura sintática;
• Adequação ao registro formal.

---

## DIRETRIZ DE AVALIAÇÃO (MENOS RIGOROSA)

- Avalie o texto de forma **global**, não penalizando excessivamente erros isolados.
- Pequenos desvios gramaticais são aceitáveis, desde que **não comprometam a compreensão**.
- Priorize a **fluidez, clareza e consistência geral da escrita**, em vez de perfeição gramatical absoluta.
- Só reduza significativamente a nota quando houver **erros frequentes, repetitivos ou que prejudiquem o entendimento**.
- Textos podem apresentar alguns desvios e ainda assim receber nota alta.

---

## TABELA DE PONTUAÇÃO

- **200 pontos**: excelente domínio, com raros desvios que não comprometem a leitura.
- **160 pontos**: bom domínio, com poucos erros perceptíveis.
- **120 pontos**: domínio mediano, com alguns erros, mas boa compreensão geral.
- **80 pontos**: domínio limitado, com erros mais frequentes que afetam parcialmente a leitura.
- **40 pontos**: domínio precário, com muitos erros que dificultam a compreensão.
- **0 ponto**: texto incompreensível ou fora da norma escrita.

---

## REGRAS

- NÃO avalie conteúdo, argumento ou repertório.
- NÃO avalie outras competências.
- NÃO seja excessivamente rigoroso com norma culta.
- Considere o nível esperado de um estudante concluinte do ensino médio.
- Penalize apenas quando houver **padrão consistente de erro**, não por ocorrências pontuais.

---

## FORMATO DE SAÍDA (JSON)
"C1": <nota inteira entre 0 e 200>,
"comentario_C1": "<comentário técnico explicando o nível atribuído, destacando padrão geral da escrita>"

---

Tema da Redação: {essay_topic}

Redação do candidato:
\n\n\n{essay_text}\n\n\n
"""