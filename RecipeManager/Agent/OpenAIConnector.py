import openai
from typing import List, Dict, Any, Optional
from openai.types.chat import (ChatCompletionUserMessageParam,
                               ChatCompletionAssistantMessageParam,
                               ChatCompletionSystemMessageParam,
                               ChatCompletionToolMessageParam,
                               ChatCompletionMessage)
import json

class OpenAIClient:
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_chat_completion(
        self,
        messages: List[ChatCompletionUserMessageParam |
                       ChatCompletionAssistantMessageParam |
                       ChatCompletionSystemMessageParam |
                       ChatCompletionToolMessageParam |
                       Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatCompletionMessage:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message

    def get_embedding(
            self,
            text: str,
            model: str = "text-embedding-3-small",
    ) -> list[float]:
        """
        Single‑string shortcut around `get_embeddings([text])[0]`.
        """
        return self.get_embeddings([text], model=model)[0]

    def get_embeddings(
        self,
        input_texts: List[str],
        model: str = "text-embedding-3-small"
    ) -> List[List[float]]:
        response = self.client.embeddings.create(
            input=input_texts,
            model=model
        )
        return [data.embedding for data in response.data]

    def get_chat_completion_json(
            self,
            messages: List[Dict[str, str]],
            model: str = "gpt-4o-mini",
            rformat: dict = None,
    ) -> Dict[str, Any]:
        """
        Same as `get_chat_completion`, but forces the assistant to return a _single_
        JSON object. The OpenAI `/chat/completions` endpoint supports the
        `response_format={"type":"json_object"}` parameter; we rely on it here so we
        do not need any brittle string‑parsing heuristics.

        Returns
        -------
        Dict[str, Any]
            Parsed JSON dictionary.
        """
        response = self.client.responses.create(
            model=model,
            input=messages,
            text=rformat,
        )
        return response


if __name__ == "__main__":
    import os

    api_key = os.environ["OPENAI_API_KEY"]
    client = OpenAIClient(api_key)
    answer = client.get_chat_completion([{'role': 'user', 'content':"Testing connection, answer just OK."}])
    print(answer.content)
    print(client.get_embeddings([answer.content]))

