import json
import re
from typing import Dict, Any, Optional
from agents import c_agents
from openai import AsyncOpenAI
import asyncio
import google.generativeai as genai


class Corrector:
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.15,
        top_p: float = 0.9,
        max_retries: int = 5,
        reasoning_effort: str = "high",
        extra_body: Optional[Dict[str, Any]] = None,
        max_concurrency: int = 10,
        provider: str = "openai",
    ):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_retries = max_retries
        self.reasoning_effort = reasoning_effort
        self.extra_body = extra_body or {}
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.provider = provider

        if provider in ("openai", "vllm"):
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
            )
        elif provider == "gemini":
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)

        self.base_system_prompt = (
            "Você DEVE responder SOMENTE com JSON válido. "
            "NÃO inclua texto extra. "
            "Siga exatamente o schema."
        )

    def _extract_json_safe(self, text: str) -> Dict:
        try:
            return json.loads(text)
        except:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))

        raise ValueError(f"JSON inválido:\n{text}")

    async def _call_model(self, prompt: str, response_format):
        async with self.semaphore:
            for attempt in range(self.max_retries):
                try:
                    if self.provider == "openai":
                        completion = await self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": self.base_system_prompt},
                                {"role": "user", "content": prompt},
                            ],
                            temperature=self.temperature,
                            top_p=self.top_p,
                            # reasoning_effort=self.reasoning_effort,
                            extra_body=self.extra_body,
                        )

                        message = completion.choices[0].message
                        raw_text = message.content.strip()
                        reasoning = getattr(message, "reasoning_content", None)

                    elif self.provider == "vllm":
                        completion = await self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": self.base_system_prompt},
                                {"role": "user", "content": prompt},
                            ],
                            extra_body=self.extra_body,
                        )

                        message = completion.choices[0].message
                        raw_text = message.content.strip()
                        # Strip <think>...</think> block if model returned one
                        raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
                        reasoning = getattr(message, "reasoning_content", None)

                    elif self.provider == "gemini":
                        full_prompt = f"{self.base_system_prompt}\n\n{prompt}"

                        response = await asyncio.to_thread(
                            self.client.generate_content,
                            full_prompt,
                        )

                        raw_text = response.text.strip()
                        reasoning = None

                    parsed = self._extract_json_safe(raw_text)
                    validated = response_format(**parsed)

                    result = validated.dict()
                    result["_reasoning"] = reasoning
                    return result

                except Exception as e:
                    print(f"[Retry {attempt+1}] erro: {e}")

        raise RuntimeError("Falha após múltiplas tentativas")

    async def execute(
        self,
        essay_text: str,
        essay_topic: str
    ) -> Dict[str, Any]:

        final_result = {}
        reasoning_log = {}

        tasks = []

        for prompt_template, response_model in c_agents:
            prompt = prompt_template.format(
                essay_text=essay_text,
                essay_topic=essay_topic
            )

            tasks.append(
                self._call_model(prompt, response_model)
            )

        results = await asyncio.gather(*tasks)

        for (prompt_template, response_model), result in zip(c_agents, results):
            reasoning_log[response_model.__name__] = result.pop("_reasoning", None)
            final_result.update(result)

        final_result["nota_final"] = sum(final_result[f"C{i}"] for i in range(1, 6))
        final_result["_full_reasoning"] = reasoning_log

        return final_result