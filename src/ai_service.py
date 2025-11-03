# src/ai_service.py
import openai
import anthropic
import requests
import json
from src import config_service

config = config_service.get_config()
prompts = config_service.get_prompts()

class AIProvider:
    def generate_summary(self, content):
        raise NotImplementedError

    def generate_blog_post(self, topic, template):
        raise NotImplementedError

class OpenAIService(AIProvider):
    def __init__(self, config):
        self.client = openai.OpenAI(api_key=config["openai_api_key"])
        self.model = config["openai_model"]

    def generate_summary(self, content):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompts["summary"]["openai"]},
                {"role": "user", "content": f"Summarize the following content:\n\n{content}"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()

    def generate_blog_post(self, topic, template):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompts["blog_post"]["openai"]},
                {"role": "user", "content": f"Generate a blog post about '{topic}' using the following template:\n\n{template}"}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()

class ClaudeService(AIProvider):
    def __init__(self, config):
        self.client = anthropic.Anthropic(api_key=config["claude_api_key"])
        self.model = config["claude_model"]

    def generate_summary(self, content):
        response = self.client.messages.create(
            model=self.model,
            system=prompts["summary"]["claude"],
            messages=[
                {"role": "user", "content": f"Summarize the following content:\n\n{content}"}
            ],
            max_tokens=150
        )
        return response.content[0].text.strip()

    def generate_blog_post(self, topic, template):
        response = self.client.messages.create(
            model=self.model,
            system=prompts["blog_post"]["claude"],
            messages=[
                {"role": "user", "content": f"Generate a blog post about '{topic}' using the following template:\n\n{template}"}
            ],
            max_tokens=500
        )
        return response.content[0].text.strip()

class DeepseekService(AIProvider):
    def __init__(self, config):
        self.client = openai.OpenAI(
            api_key=config["deepseek_api_key"],
            base_url="https://api.deepseek.com"
        )
        self.model = config["deepseek_model"]

    def generate_summary(self, content):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompts["summary"]["deepseek"]},
                {"role": "user", "content": f"Summarize the following content:\n\n{content}"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()

    def generate_blog_post(self, topic, template):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompts["blog_post"]["deepseek"]},
                {"role": "user", "content": f"Generate a blog post about '{topic}' using the following template:\n\n{template}"}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()

class OllamaService(AIProvider):
    def __init__(self, config):
        self.base_url = config["ollama_base_url"]
        self.model = config["ollama_model"]

    def _generate(self, system_prompt, user_prompt):
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            if "model not found" in e.response.text:
                raise ValueError(f"Model '{self.model}' not found in Ollama.")
            raise e


    def generate_summary(self, content):
        return self._generate(
            prompts["summary"]["ollama"],
            f"Summarize the following content:\n\n{content}"
        )

    def generate_blog_post(self, topic, template):
        return self._generate(
            prompts["blog_post"]["ollama"],
            f"Generate a blog post about '{topic}' using the following template:\n\n{template}"
        )

def get_ai_service(config):
    provider = config.get("provider")
    if provider == "openai":
        return OpenAIService(config)
    elif provider == "claude":
        return ClaudeService(config)
    elif provider == "deepseek":
        return DeepseekService(config)
    elif provider == "ollama":
        return OllamaService(config)
    else:
        raise ValueError(f"Unknown AI provider: {provider}")

def validate_api_keys(config):
    errors = []

    # Validate OpenAI API key
    try:
        client = openai.OpenAI(api_key=config["openai_api_key"])
        client.models.list()
    except Exception as e:
        errors.append(f"OpenAI API key is invalid: {e}")

    # Validate Claude API key
    try:
        client = anthropic.Anthropic(api_key=config["claude_api_key"])
        client.models.list()
    except Exception as e:
        errors.append(f"Claude API key is invalid: {e}")

    # Validate Deepseek API key
    try:
        client = openai.OpenAI(
            api_key=config["deepseek_api_key"],
            base_url="https://api.deepseek.com"
        )
        client.models.list()
    except Exception as e:
        errors.append(f"Deepseek API key is invalid: {e}")

    return errors
