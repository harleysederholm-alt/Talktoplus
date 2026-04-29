class UserMessage:
    def __init__(self, text: str):
        self.text = text

class LlmChat:
    def __init__(self, api_key: str, session_id: str, system_message: str):
        pass
    def with_model(self, provider: str, model: str):
        return self
    async def send_message(self, message: UserMessage):
        raise Exception("Mock LLM: emergentintegrations not installed")
