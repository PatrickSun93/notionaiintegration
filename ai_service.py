"""
AI Service Module - Notion AI Integration

This module provides a unified interface for interacting with multiple AI providers
including OpenAI, Claude, Deepseek, and Ollama.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def chat_with_context(self, message: str, context: str = "") -> str:
        """Chat with AI using provided context."""
        pass
    
    @abstractmethod
    def generate_summary(self, content: str) -> str:
        """Generate a summary of the provided content."""
        pass
    
    @abstractmethod
    def generate_blog_post(self, topic: str, template: str = "") -> str:
        """Generate a blog post on the given topic."""
        pass


class OpenAIService(AIProvider):
    """OpenAI provider implementation using Chat Completions API."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
        self.model = model
        self.max_retries = 3
        self.retry_delay = 1
    
    def _make_request_with_retry(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        import openai
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
                
            except openai.RateLimitError as e:
                logger.warning(f"OpenAI rate limit hit, attempt {attempt + 1}/{self.max_retries}")
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    
            except openai.APIError as e:
                logger.error(f"OpenAI API error: {e}")
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                logger.error(f"Unexpected error in OpenAI request: {e}")
                last_exception = e
                break
        
        raise Exception(f"OpenAI request failed after {self.max_retries} attempts: {last_exception}")
    
    def chat_with_context(self, message: str, context: str = "") -> str:
        messages = []
        if context:
            messages.append({
                "role": "system",
                "content": f"You are a helpful assistant. Use the following context from Notion to inform your responses:\n\n{context}"
            })
        messages.append({"role": "user", "content": message})
        return self._make_request_with_retry(messages)
    
    def generate_summary(self, content: str) -> str:
        messages = [
            {"role": "system", "content": "You are a helpful assistant that creates concise, informative summaries. Focus on the key points and main ideas."},
            {"role": "user", "content": f"Please summarize the following content:\n\n{content}"}
        ]
        return self._make_request_with_retry(messages, max_tokens=500)
    
    def generate_blog_post(self, topic: str, template: str = "") -> str:
        system_prompt = "You are a skilled content writer. Create engaging, well-structured blog posts with clear headings and informative content."
        if template:
            system_prompt += f" Follow this template structure:\n\n{template}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Write a comprehensive blog post about: {topic}"}
        ]
        return self._make_request_with_retry(messages, max_tokens=2000)


class ClaudeService(AIProvider):
    """Claude provider implementation using Anthropic SDK."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
        self.model = model
        self.max_retries = 3
        self.retry_delay = 1
    
    def _make_request_with_retry(self, messages: List[Dict[str, str]], max_tokens: int = 1000, system: str = "") -> str:
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                formatted_messages = []
                for msg in messages:
                    if msg["role"] != "system":
                        formatted_messages.append({"role": msg["role"], "content": msg["content"]})
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    system=system,
                    messages=formatted_messages
                )
                return response.content[0].text.strip()
                
            except Exception as e:
                error_str = str(e).lower()
                if "rate limit" in error_str or "429" in error_str:
                    logger.warning(f"Claude rate limit hit, attempt {attempt + 1}/{self.max_retries}")
                    last_exception = e
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                elif "api" in error_str or "400" in error_str or "401" in error_str:
                    logger.error(f"Claude API error: {e}")
                    last_exception = e
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                else:
                    logger.error(f"Unexpected error in Claude request: {e}")
                    last_exception = e
                    break
        
        raise Exception(f"Claude request failed after {self.max_retries} attempts: {last_exception}")
    
    def chat_with_context(self, message: str, context: str = "") -> str:
        system_message = "You are a helpful assistant."
        if context:
            system_message += f" Use the following context from Notion to inform your responses:\n\n{context}"
        messages = [{"role": "user", "content": message}]
        return self._make_request_with_retry(messages, system=system_message)
    
    def generate_summary(self, content: str) -> str:
        system_message = "You are a helpful assistant that creates concise, informative summaries. Focus on the key points and main ideas."
        messages = [{"role": "user", "content": f"Please summarize the following content:\n\n{content}"}]
        return self._make_request_with_retry(messages, max_tokens=500, system=system_message)
    
    def generate_blog_post(self, topic: str, template: str = "") -> str:
        system_message = "You are a skilled content writer. Create engaging, well-structured blog posts with clear headings and informative content."
        if template:
            system_message += f" Follow this template structure:\n\n{template}"
        messages = [{"role": "user", "content": f"Write a comprehensive blog post about: {topic}"}]
        return self._make_request_with_retry(messages, max_tokens=2000, system=system_message)


class DeepseekService(AIProvider):
    """Deepseek provider implementation using HTTP client."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_retries = 3
        self.retry_delay = 1
    
    def _make_request_with_retry(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        import requests
        last_exception = None
        
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7}
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
                elif response.status_code == 429:
                    logger.warning(f"Deepseek rate limit hit, attempt {attempt + 1}/{self.max_retries}")
                    last_exception = Exception(f"Rate limit error: {response.text}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    logger.error(f"Deepseek API error {response.status_code}: {response.text}")
                    last_exception = Exception(f"API error {response.status_code}: {response.text}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        
            except Exception as e:
                logger.error(f"Error in Deepseek request: {e}")
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        raise Exception(f"Deepseek request failed after {self.max_retries} attempts: {last_exception}")
    
    def chat_with_context(self, message: str, context: str = "") -> str:
        messages = []
        if context:
            messages.append({"role": "system", "content": f"You are a helpful assistant. Use the following context from Notion to inform your responses:\n\n{context}"})
        messages.append({"role": "user", "content": message})
        return self._make_request_with_retry(messages)
    
    def generate_summary(self, content: str) -> str:
        messages = [
            {"role": "system", "content": "You are a helpful assistant that creates concise, informative summaries. Focus on the key points and main ideas."},
            {"role": "user", "content": f"Please summarize the following content:\n\n{content}"}
        ]
        return self._make_request_with_retry(messages, max_tokens=500)
    
    def generate_blog_post(self, topic: str, template: str = "") -> str:
        system_prompt = "You are a skilled content writer. Create engaging, well-structured blog posts with clear headings and informative content."
        if template:
            system_prompt += f" Follow this template structure:\n\n{template}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Write a comprehensive blog post about: {topic}"}
        ]
        return self._make_request_with_retry(messages, max_tokens=2000)


class OllamaService(AIProvider):
    """Ollama provider implementation for local installations."""
    
    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama2"):
        self.endpoint = endpoint.rstrip('/')
        self.model = model
        self.max_retries = 3
        self.retry_delay = 1
    
    def _make_request_with_retry(self, prompt: str, system: str = "") -> str:
        import requests
        last_exception = None
        
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(f"{self.endpoint}/api/generate", json=payload, timeout=60)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["response"].strip()
                else:
                    logger.error(f"Ollama API error {response.status_code}: {response.text}")
                    last_exception = Exception(f"API error {response.status_code}: {response.text}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        
            except Exception as e:
                if "ConnectionError" in str(type(e)):
                    logger.error(f"Cannot connect to Ollama at {self.endpoint}: {e}")
                    last_exception = Exception(f"Ollama connection failed. Is Ollama running at {self.endpoint}?")
                    break
                else:
                    logger.error(f"Error in Ollama request: {e}")
                    last_exception = e
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
        
        raise Exception(f"Ollama request failed after {self.max_retries} attempts: {last_exception}")
    
    def chat_with_context(self, message: str, context: str = "") -> str:
        system_message = "You are a helpful assistant."
        if context:
            system_message += f" Use the following context from Notion to inform your responses:\n\n{context}"
        return self._make_request_with_retry(message, system=system_message)
    
    def generate_summary(self, content: str) -> str:
        system_message = "You are a helpful assistant that creates concise, informative summaries. Focus on the key points and main ideas."
        prompt = f"Please summarize the following content:\n\n{content}"
        return self._make_request_with_retry(prompt, system=system_message)
    
    def generate_blog_post(self, topic: str, template: str = "") -> str:
        system_message = "You are a skilled content writer. Create engaging, well-structured blog posts with clear headings and informative content."
        if template:
            system_message += f" Follow this template structure:\n\n{template}"
        prompt = f"Write a comprehensive blog post about: {topic}"
        return self._make_request_with_retry(prompt, system=system_message)


def get_ai_service(config: Optional[Dict[str, Any]] = None) -> AIProvider:
    """Factory function to get AI service based on configuration."""
    if config is None:
        try:
            from config.ai_config import get_config
            config = get_config()
        except ImportError:
            raise ImportError("Configuration module not available")
    
    provider = config.get("provider", "openai").lower()
    
    try:
        if provider == "openai":
            api_key = config.get("openai_api_key")
            if not api_key:
                raise ValueError("OpenAI API key is required")
            return OpenAIService(api_key)
            
        elif provider == "claude":
            api_key = config.get("claude_api_key")
            if not api_key:
                raise ValueError("Claude API key is required")
            return ClaudeService(api_key)
            
        elif provider == "deepseek":
            api_key = config.get("deepseek_api_key")
            if not api_key:
                raise ValueError("Deepseek API key is required")
            return DeepseekService(api_key)
            
        elif provider == "ollama":
            endpoint = config.get("ollama_endpoint", "http://localhost:11434")
            model = config.get("ollama_model", "llama2")
            return OllamaService(endpoint, model)
            
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
            
    except Exception as e:
        logger.error(f"Failed to initialize AI service for provider '{provider}': {e}")
        raise


def get_available_providers() -> List[str]:
    """Get list of available AI providers."""
    return ["openai", "claude", "deepseek", "ollama"]


def validate_provider_config(provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate configuration for a specific provider."""
    result = {"valid": False, "message": ""}
    
    try:
        if provider == "openai":
            api_key = config.get("openai_api_key")
            if not api_key:
                result["message"] = "OpenAI API key is required"
            elif not api_key.startswith("sk-"):
                result["message"] = "Invalid OpenAI API key format"
            else:
                result["valid"] = True
                result["message"] = "OpenAI configuration is valid"
                
        elif provider == "claude":
            api_key = config.get("claude_api_key")
            if not api_key:
                result["message"] = "Claude API key is required"
            elif not api_key.startswith("sk-ant-"):
                result["message"] = "Invalid Claude API key format"
            else:
                result["valid"] = True
                result["message"] = "Claude configuration is valid"
                
        elif provider == "deepseek":
            api_key = config.get("deepseek_api_key")
            if not api_key:
                result["message"] = "Deepseek API key is required"
            elif not api_key.startswith("sk-"):
                result["message"] = "Invalid Deepseek API key format"
            else:
                result["valid"] = True
                result["message"] = "Deepseek configuration is valid"
                
        elif provider == "ollama":
            endpoint = config.get("ollama_endpoint", "http://localhost:11434")
            if not endpoint:
                result["message"] = "Ollama endpoint is required"
            else:
                result["valid"] = True
                result["message"] = "Ollama configuration is valid"
                
        else:
            result["message"] = f"Unsupported provider: {provider}"
            
    except Exception as e:
        result["message"] = f"Validation error: {str(e)}"
        logger.error(f"Error validating {provider} config: {e}")
    
    return result