# src/ai_service.py
import openai
from config.ai_config import get_config

config = get_config()
openai.api_key = config["openai_api_key"]

class AIProvider:
    def generate_summary(self, content):
        raise NotImplementedError

    def generate_blog_post(self, topic, template):
        raise NotImplementedError

class OpenAIService(AIProvider):
    def generate_summary(self, content):
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Summarize the following content:\n\n{content}",
            max_tokens=150
        )
        return response.choices[0].text.strip()

    def generate_blog_post(self, topic, template):
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Generate a blog post about '{topic}' using the following template:\n\n{template}",
            max_tokens=500
        )
        return response.choices[0].text.strip()

class ClaudeService(AIProvider):
    def generate_summary(self, content):
        # TODO: Implement Claude summary generation
        return "Claude summary"

    def generate_blog_post(self, topic, template):
        # TODO: Implement Claude blog post generation
        return f"Blog post about {topic} using {template}"

class DeepseekService(AIProvider):
    def generate_summary(self, content):
        # TODO: Implement Deepseek summary generation
        return "Deepseek summary"

    def generate_blog_post(self, topic, template):
        # TODO: Implement Deepseek blog post generation
        return f"Blog post about {topic} using {template}"

class OllamaService(AIProvider):
    def generate_summary(self, content):
        # TODO: Implement Ollama summary generation
        return "Ollama summary"

    def generate_blog_post(self, topic, template):
        # TODO: Implement Ollama blog post generation
        return f"Blog post about {topic} using {template}"

def get_ai_service(config):
    provider = config.get("provider")
    if provider == "openai":
        return OpenAIService()
    elif provider == "claude":
        return ClaudeService()
    elif provider == "deepseek":
        return DeepseekService()
    elif provider == "ollama":
        return OllamaService()
    else:
        raise ValueError(f"Unknown AI provider: {provider}")
