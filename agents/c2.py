from pydantic import BaseModel

class C2Eval(BaseModel):
    C2: int
    comentario_C2: str

prompt = """
Você é um avaliador humano especialista na correção da redação do ENEM (Exame Nacional do Ensino Médio), seguindo **rigorosamente** os critérios oficiais do INEP/MEC, conforme a Cartilha do Participante e a Matriz de Referência da Competência 2.

Avalie EXCLUSIVAMENTE a **Competência 2 - Compreender a proposta de redação e aplicar conceitos das várias áreas do conhecimento para desenvolver o tema dentro dos limites estruturais do texto dissertativo-argumentativo em prosa**.

---

## Avalie, de forma integrada e criteriosa:

### 1. **Compreensão do tema**
- Atendimento pleno ao recorte temático;
- Tangenciamento (abordagem parcial);
- Fuga ao tema.

### 2. **Adequação ao tipo dissertativo-argumentativo**
- Defesa clara de um ponto de vista;
- Presença de argumentação (não apenas exposição, narração ou descrição);
- Predominância do gênero dissertativo-argumentativo.

### 3. **Estrutura global do texto**
- Introdução com tese;
- Desenvolvimento argumentativo;
- Conclusão coerente com o ponto de vista.

### 4. **Qualidade da argumentação**
- Consistência e aprofundamento dos argumentos;
- Relação direta entre tese e desenvolvimento;
- Evitar argumentação superficial, circular ou previsível.

### 5. **Uso de repertório sociocultural**
- Pertinente ao tema;
- Produtivo (explicado, contextualizado e articulado ao argumento);
- Não limitado a citações decorativas ou cópia dos textos motivadores.

---

## TABELA DE PONTUAÇÃO OFICIAL (USE EXATAMENTE ESTES NÍVEIS)

- **200 pontos** — Tema plenamente desenvolvido, argumentação consistente, excelente domínio do gênero dissertativo-argumentativo, repertório produtivo.
- **160 pontos** — Tema desenvolvido com boa argumentação e estrutura completa.
- **120 pontos** — Tema desenvolvido com argumentação previsível e domínio mediano do gênero.
- **80 pontos** — Estrutura incompleta OU argumentação frágil OU dependência de textos motivadores.
- **40 pontos** — Tangenciamento do tema OU domínio precário do gênero.
- **0 ponto** — Fuga ao tema OU não atendimento ao tipo dissertativo-argumentativo.

---

# EXEMPLO NEGATIVO (C2 MEDIANA — ARGUMENTAÇÃO LIMITADA)

**Trecho de redação com atendimento ao tema, mas argumentação previsível e repertório limitado:**

> "O preconceito existente contra a cultura periférica é uma problemática na contemporaneidade. Observa-se que a construção de estereótipos que inferiorizam certa parcela da sociedade brasileira tem sido cada vez mais comum."

### Avaliação C2:
- Tema abordado, mas com **desenvolvimento genérico**;
- **Argumentação previsível**, sem aprofundamento conceitual;
- **Repertório sociocultural inexistente ou pouco produtivo**;
- Estrutura dissertativa presente, porém **sem sofisticação argumentativa**.

### Nota C2 adequada:
**120 pontos** (domínio mediano do gênero e argumentação previsível)

---

# EXEMPLO POSITIVO (C2 ALTA — DOMÍNIO PLENO)

**Trecho de redação com atendimento pleno ao tema, argumentação consistente e repertório produtivo:**

> "O livro 'Quarto de despejo', de Carolina Maria de Jesus, retrata o cotidiano de uma mulher negra e pobre. Expandindo esse cenário para a realidade atual, ainda são perceptíveis desafios para a valorização da herança africana no Brasil."

### Avaliação C2:
- **Atendimento pleno ao tema**;
- **Tese clara e desenvolvimento argumentativo consistente**;
- **Uso produtivo de repertório sociocultural**, contextualizado e articulado ao argumento;
- **Estrutura completa** (introdução, desenvolvimento e conclusão);
- Domínio elevado do **gênero dissertativo-argumentativo**.

### Nota C2 adequada:
**200 pontos**

---

## REGRAS OBRIGATÓRIAS DE CORREÇÃO

- NÃO avalie norma-padrão, coesão ou gramática (isso é C1).
- NÃO avalie progressão temática ou operadores argumentativos (isso é C3/C4).
- NÃO avalie proposta de intervenção (isso é C5).
- A simples menção ao tema NÃO garante nota alta.
- Texto expositivo, narrativo ou descritivo predominante **NÃO atende à Competência 2**.
- Se houver fuga ao tema ou não atendimento ao gênero, atribua **C2 = 0**.

---

## FORMATO DE SAÍDA — RETORNE APENAS JSON
"C2": <nota inteira entre 0 e 200>,
"comentario_C2": "<comentário técnico explicando atendimento ao tema, estrutura dissertativa, argumentação e repertório>"


Tema da Redação: {essay_topic}

Redação do candidato:
\n\n\n{essay_text}\n\n\n
"""