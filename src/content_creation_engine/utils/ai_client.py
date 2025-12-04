"""
Multi-provider AI client supporting OpenAI, DeepSeek, and Grok.
Provides a unified interface for content generation.
"""

from typing import Any, Dict, List, Optional
from enum import Enum
import json
import logging
import re

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GROK = "grok"


class AIClient:
    """
    Unified AI client supporting multiple providers.
    Automatically handles provider-specific configurations.
    """
    
    # Provider configurations
    PROVIDER_CONFIGS = {
        AIProvider.OPENAI: {
            "base_url": None,  # Use default
            "default_model": "gpt-4",
            "supports_json_mode": True
        },
        AIProvider.DEEPSEEK: {
            "base_url": "https://api.deepseek.com",
            "default_model": "deepseek-chat",
            "supports_json_mode": True
        },
        AIProvider.GROK: {
            "base_url": "https://api.x.ai/v1",
            "default_model": "grok-beta",
            "supports_json_mode": False
        }
    }
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize the AI client.
        
        Args:
            provider: AI provider name (openai, deepseek, grok)
            api_key: API key for the provider
            model: Model name to use (uses default if not specified)
        """
        try:
            self.provider = AIProvider(provider.lower())
        except ValueError:
            logger.warning(f"Unknown provider '{provider}', defaulting to OpenAI")
            self.provider = AIProvider.OPENAI
        
        self.api_key = api_key
        self.config = self.PROVIDER_CONFIGS[self.provider]
        self.model = model or self.config["default_model"]
        self.client = None
        
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the OpenAI-compatible client."""
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI package not installed. Install with: pip install openai")
            return
        
        if not self.api_key:
            logger.warning(f"No API key provided for {self.provider.value}")
            return
        
        try:
            client_kwargs = {"api_key": self.api_key}
            
            if self.config["base_url"]:
                client_kwargs["base_url"] = self.config["base_url"]
            
            self.client = OpenAI(**client_kwargs)
            logger.info(f"Initialized {self.provider.value} client with model {self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False
    ) -> Optional[str]:
        """
        Generate content using the AI model.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Creativity level (0-1)
            max_tokens: Maximum response length
            json_mode: Whether to enforce JSON output
            
        Returns:
            Generated text or None if failed
        """
        if not self.client:
            logger.error("AI client not initialized")
            return None
        
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Add JSON mode if supported and requested
            if json_mode and self.config["supports_json_mode"]:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            
            logger.info(f"Generated {len(content)} characters using {self.provider.value}")
            
            return content
            
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            return None
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Optional[Dict[str, Any]]:
        """
        Generate and parse JSON content.
        
        Args:
            prompt: User prompt (should request JSON output)
            system_prompt: System prompt for context
            temperature: Creativity level (0-1)
            max_tokens: Maximum response length
            
        Returns:
            Parsed JSON as dictionary or None if failed
        """
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=self.config["supports_json_mode"]
        )
        
        if not response:
            return None
        
        try:
            # Try to extract JSON from the response
            # Handle cases where JSON might be wrapped in markdown code blocks
            json_str = response
            
            # Remove markdown code blocks if present
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            return json.loads(json_str.strip())
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response}")
            
            # Try to extract JSON array or object
            try:
                # Find JSON array
                match = re.search(r'\[[\s\S]*\]', response)
                if match:
                    return json.loads(match.group())
                
                # Find JSON object
                match = re.search(r'\{[\s\S]*\}', response)
                if match:
                    return json.loads(match.group())
            except:
                pass
            
            return None
    
    def generate_with_retry(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
        **kwargs
    ) -> Optional[str]:
        """
        Generate content with automatic retry on failure.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments for generate()
            
        Returns:
            Generated text or None if all retries failed
        """
        for attempt in range(max_retries):
            result = self.generate(prompt, system_prompt, **kwargs)
            if result:
                return result
            
            logger.warning(f"Generation attempt {attempt + 1}/{max_retries} failed")
        
        return None
    
    @classmethod
    def from_settings(cls, settings) -> "AIClient":
        """
        Create an AIClient from application settings.
        
        Args:
            settings: Settings object with AI configuration
            
        Returns:
            Configured AIClient instance
        """
        provider = settings.ai.default_provider.lower()
        
        # Get the appropriate API key
        api_key = None
        model = None
        
        if provider == "openai":
            api_key = settings.ai.openai_api_key
            model = settings.ai.openai_model
        elif provider == "deepseek":
            api_key = settings.ai.deepseek_api_key
            model = settings.ai.deepseek_model
        elif provider == "grok":
            api_key = settings.ai.grok_api_key
            model = settings.ai.grok_model
        
        return cls(provider=provider, api_key=api_key, model=model)
