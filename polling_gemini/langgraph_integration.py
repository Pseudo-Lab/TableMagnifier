"""
LangGraph Integration Module
GeminiAPIPool을 LangGraph와 쉽게 통합할 수 있도록 하는 래퍼 클래스
"""

import asyncio
from typing import Optional, Dict, Any, List, TypedDict, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from .api_pool import get_gemini_pool, GeminiAPIPool


class GeminiPoolChatModel(BaseChatModel):
    """
    LangGraph/LangChain과 호환되는 Gemini API Pool Chat Model
    
    GeminiAPIPool을 사용하여 자동으로 API 키를 로테이션하면서
    LangGraph의 ChatModel 인터페이스를 구현합니다.
    """
    
    api_pool: Optional[GeminiAPIPool] = None
    config_path: Optional[str] = None
    model_kwargs: Dict[str, Any] = {}
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        **kwargs
    ):
        """
        Args:
            config_path: API 키 설정 파일 경로
            **kwargs: 추가 모델 파라미터
        """
        super().__init__(**kwargs)
        self.config_path = config_path
        self.model_kwargs = kwargs
        self._initialize_pool()
    
    def _initialize_pool(self):
        """API Pool 초기화"""
        if self.api_pool is None:
            self.api_pool = get_gemini_pool(self.config_path)
    
    def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> List[Any]:
        """LangChain 메시지를 Gemini 프롬프트(Content parts list)로 변환"""
        prompt_parts = []
        
        for message in messages:
            content = message.content
            if isinstance(content, str):
                # 텍스트 메시지
                text_part = ""
                if isinstance(message, SystemMessage):
                    text_part = f"System: {content}\n"
                elif isinstance(message, HumanMessage):
                    text_part = f"{content}\n"
                elif isinstance(message, AIMessage):
                    text_part = f"Assistant: {content}\n"
                else:
                    text_part = f"{content}\n"
                prompt_parts.append(text_part)
                
            elif isinstance(content, list):
                # 멀티모달 메시지 (리스트)
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type")
                        if item_type == "text":
                            prompt_parts.append(item.get("text", ""))
                        elif item_type == "image_url":
                            image_url = item.get("image_url", {})
                            url = image_url if isinstance(image_url, str) else image_url.get("url")
                            
                            if url and url.startswith("data:"):
                                # data:image/png;base64,......
                                try:
                                    header, base64_data = url.split(",", 1)
                                    mime_type = header.split(":")[1].split(";")[0]
                                    
                                    # Gemini API expects: {'mime_type': ..., 'data': b'...'}
                                    import base64
                                    prompt_parts.append({
                                        "mime_type": mime_type,
                                        "data": base64.b64decode(base64_data)
                                    })
                                except Exception as e:
                                    # 파싱 실패 시 텍스트로 남김 (디버깅용)
                                    prompt_parts.append(f"[Image parse error: {e}]")
            else:
                prompt_parts.append(str(content))
        
        return prompt_parts
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs
    ) -> ChatResult:
        """
        메시지 리스트로부터 응답 생성
        
        Args:
            messages: 입력 메시지 리스트
            stop: 중지 시퀀스
            run_manager: 실행 매니저 (콜백용)
            **kwargs: 추가 생성 파라미터
            
        Returns:
            ChatResult 객체
        """
        # 메시지를 프롬프트로 변환
        prompt = self._convert_messages_to_prompt(messages)
        
        # 모델 파라미터 병합
        generation_params = {**self.model_kwargs, **kwargs}
        
        # API Pool을 통해 컨텐츠 생성
        try:
            response_text = self.api_pool.generate_content(
                prompt,
                **generation_params
            )
            
            # ChatResult 형식으로 변환
            message = AIMessage(content=response_text)
            generation = ChatGeneration(message=message)
            
            return ChatResult(generations=[generation])
            
        except Exception as e:
            raise RuntimeError(f"Gemini API 호출 실패: {e}")
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs
    ) -> ChatResult:
        """비동기 메시지 생성"""
        # 메시지를 프롬프트로 변환
        prompt = self._convert_messages_to_prompt(messages)
        
        # 모델 파라미터 병합
        generation_params = {**self.model_kwargs, **kwargs}
        
        # API Pool을 통해 비동기로 컨텐츠 생성
        try:
            response_text = await self.api_pool.agenerate_content(
                prompt,
                **generation_params
            )
            
            # ChatResult 형식으로 변환
            message = AIMessage(content=response_text)
            generation = ChatGeneration(message=message)
            
            return ChatResult(generations=[generation])
            
        except Exception as e:
            raise RuntimeError(f"Gemini API 호출 실패: {e}")
    
    @property
    def _llm_type(self) -> str:
        """LLM 타입 반환"""
        return "gemini-pool"
    
    def get_num_tokens(self, text: str) -> int:
        """토큰 수 추정 (대략적)"""
        # 간단한 추정: 4글자당 1토큰
        return len(text) // 4
    
    def get_pool_status(self) -> Dict[str, Any]:
        """현재 API Pool 상태 반환"""
        if self.api_pool:
            return {
                'current_key': self.api_pool.get_current_key_info(),
                'all_keys': self.api_pool.get_all_keys_status()
            }
        return {}


def create_gemini_chat_model(
    config_path: Optional[str] = None,
    **kwargs
) -> GeminiPoolChatModel:
    """
    Gemini Pool Chat Model 생성 헬퍼 함수
    
    Args:
        config_path: API 키 설정 파일 경로
        **kwargs: 추가 모델 파라미터
        
    Returns:
        GeminiPoolChatModel 인스턴스
        
    Example:
        ```python
        from pulling_gemini import create_gemini_chat_model
        
        # 모델 생성
        model = create_gemini_chat_model()
        
        # LangGraph에서 사용
        from langgraph.graph import StateGraph
        
        def my_node(state):
            response = model.invoke([HumanMessage(content="Hello!")])
            return {"messages": [response]}
        ```
    """
    return GeminiPoolChatModel(config_path=config_path, **kwargs)


# 간단한 사용을 위한 래퍼 함수
def invoke_gemini(
    prompt: str,
    config_path: Optional[str] = None,
    **kwargs
) -> str:
    """
    간단하게 Gemini API를 호출하는 함수 (동기)
    
    Args:
        prompt: 입력 프롬프트
        config_path: API 키 설정 파일 경로
        **kwargs: 추가 생성 파라미터
        
    Returns:
        생성된 텍스트
        
    Example:
        ```python
        from pulling_gemini import invoke_gemini
        
        response = invoke_gemini("Tell me a joke")
        print(response)
        ```
    """
    pool = get_gemini_pool(config_path)
    return pool.generate_content(prompt, **kwargs)


async def ainvoke_gemini(
    prompt: str,
    config_path: Optional[str] = None,
    **kwargs
) -> str:
    """
    간단하게 Gemini API를 비동기로 호출하는 함수
    
    Args:
        prompt: 입력 프롬프트
        config_path: API 키 설정 파일 경로
        **kwargs: 추가 생성 파라미터
        
    Returns:
        생성된 텍스트
        
    Example:
        ```python
        from pulling_gemini import ainvoke_gemini
        import asyncio
        
        async def main():
            response = await ainvoke_gemini("Tell me a joke")
            print(response)
        
        asyncio.run(main())
        ```
    """
    pool = get_gemini_pool(config_path)
    return await pool.agenerate_content(prompt, **kwargs)
