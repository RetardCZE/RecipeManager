from typing import List, Dict, Optional, Any
from RecipeManager.Agent.OpenAIConnector import OpenAIClient
from RecipeManager.Knowledge.UserManager import CustomerSession
from RecipeManager.Knowledge.ShopManager import ShopManager
from RecipeManager.Knowledge.models import get_session


from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
    ChatCompletionMessageToolCallParam
)

class GeneralAgent(OpenAIClient):
    def __init__(self, api_key: str, session):
        super().__init__(api_key)
        self.session = session
        self.system_message: Optional[ChatCompletionMessageParam] = None
        self.history: List[ChatCompletionMessageParam] = []
        self.max_loops: int = 5

    def set_system_message(self, content: str) -> None:
        self.system_message = {"role": "system", "content": content}

    def add_user_message(self, content: str) -> None:
        user_message = {"role": "user", "content": content}
        self.history.append(user_message)
        self.evaluate()

    def add_assistant_message(self, message: Dict[str, Any]) -> None:
        assistant_message = {
            "role": "assistant",
            "content": message.get("content")
        }

        if "tool_calls" in message:
            assistant_message["tool_calls"] = message["tool_calls"]

        self.history.append(assistant_message)

        if "tool_calls" in message:
            for tool_call in message["tool_calls"]:
                self.resolve_tool_call(tool_call)

    def add_tool_message(self, tool_call_id: str, content: str) -> None:
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content
        }
        self.history.append(tool_message)

    def resolve_tool_call(self, tool_call: ChatCompletionMessageToolCallParam) -> None:
        # Dummy implementation: should be replaced with actual tool handling
        tool_response = f"Executed tool {tool_call.function.name} with arguments {tool_call.function.arguments}"
        self.add_tool_message(tool_call_id=tool_call.id, content=tool_response)

    def evaluate(self) -> None:
        if not self.system_message:
            raise ValueError("System message must be set before evaluation.")

        loop_count = 0

        while loop_count < self.max_loops:
            messages = [self.system_message] + self.history
            assistant_response = self.get_chat_completion(messages=messages)

            # Simulate parsing for tool calls
            # In real implementation, you'd use OpenAI's full response object
            parsed_response = {"content": assistant_response}  # Replace with parsing logic as needed
            self.add_assistant_message(parsed_response)

            last_message = self.history[-1]
            if last_message["role"] == "assistant" and "tool_calls" not in last_message:
                break

            loop_count += 1

        if loop_count >= self.max_loops:
            print("Max tool-use loops reached. Forcing completion without tools.")


if __name__ == "__main__":
    import os

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

    agent = GeneralAgent(api_key=api_key)
    agent.set_system_message("You are a helpful assistant.")
    agent.add_user_message("What is the capital of France?")
    print(agent.history)
