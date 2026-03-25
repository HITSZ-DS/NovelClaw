"""
LLM 客户端封装，支持 Codex/OpenAI/DeepSeek（默认指向 packycode Codex）
"""
from typing import List, Dict, Optional
import time
from openai import OpenAI
from config import Config


class LLMClient:
    """LLM API 客户端封装"""
    
    def __init__(self, config: Config):
        self.config = config
        timeout_seconds = getattr(config, "llm_timeout_seconds", 0)
        client_timeout = None if timeout_seconds <= 0 else timeout_seconds
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.api_base_url,
            timeout=client_timeout,
            max_retries=getattr(config, "llm_max_retries", 1),
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        调用 LLM 进行对话
        """
        max_t = max_tokens if max_tokens is not None else self.config.max_tokens
        if max_t is None:
            max_t = 2000
        max_t = min(max_t, 8000)
        messages = list(messages)
        if self.config.language.startswith("en"):
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": "You are an English-language assistant. Always respond in English, even if the user prompt mixes other languages.",
                },
            )
        elif self.config.language.startswith("zh"):
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": "你是一名中文助手，请始终使用中文回答，即便用户提示混杂其他语言。",
                },
            )
        try:
            if getattr(self.config, "llm_call_log", True):
                timeout_display = "disabled" if getattr(self.config, "llm_timeout_seconds", 0) <= 0 else f"{getattr(self.config, 'llm_timeout_seconds', 0)}s"
                print(
                    f"[LLM] start provider={self.config.llm_provider} "
                    f"model={model or self.config.model_name} "
                    f"wire={getattr(self.config, 'wire_api', 'chat')} "
                    f"timeout={timeout_display}"
                )
            started = time.perf_counter()
            if getattr(self.config, "wire_api", "chat") == "responses":
                # 将 messages 展开为文本输入，尽量保留角色信息
                joined = "\n".join([f"{m.get('role','user').upper()}: {m.get('content','')}" for m in messages])
                response = self.client.responses.create(
                    model=model or self.config.model_name,
                    input=joined,
                    max_output_tokens=max_t,
                    temperature=temperature if temperature is not None else self.config.temperature,
                    reasoning={"effort": getattr(self.config, "model_reasoning_effort", "high") if hasattr(self.config, "model_reasoning_effort") else "high"},
                )
                output = response.output_text
            else:
                response = self.client.chat.completions.create(
                    model=model or self.config.model_name,
                    messages=messages,
                    temperature=temperature if temperature is not None else self.config.temperature,
                    max_tokens=max_t
                )
                output = response.choices[0].message.content
            if getattr(self.config, "llm_call_log", True):
                cost = time.perf_counter() - started
                print(f"[LLM] done model={model or self.config.model_name} elapsed={cost:.2f}s")
            return output
        except Exception as e:
            if getattr(self.config, "llm_call_log", True):
                cost = time.perf_counter() - started
                print(f"[LLM] failed model={model or self.config.model_name} elapsed={cost:.2f}s err={e}")
            raise Exception(f"LLM 调用失败: {str(e)}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        生成文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self.chat(messages, temperature, max_tokens)
