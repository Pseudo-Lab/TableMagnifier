"""
LangGraph Integration Module
GeminiAPIPool을 LangGraph와 쉽게 통합할 수 있도록 하는 래퍼 클래스
"""

import asyncio
import base64
from typing import Optional, Dict, Any, List, TypedDict, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from .api_pool import get_gemini_pool, GeminiAPIPool

# PIL Image import for multimodal support
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class GeminiPoolChatModel(BaseChatModel):
    """
    LangGraph/LangChain과 호환되는 Gemini API Pool Chat Model
    
    GeminiAPIPool을 사용하여 자동으로 API 키를 로테이션하면서
    LangGraph의 ChatModel 인터페이스를 구현합니다.
    멀티모달(이미지 포함) 메시지를 지원합니다.
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
    
    def _convert_messages_to_gemini_content(self, messages: List[BaseMessage]) -> List[Any]:
        """
        LangChain 메시지를 Gemini API 형식으로 변환 (멀티모달 지원)
        
        지원하는 형식:
        - 텍스트 메시지
        - 이미지 URL (data:image/... 형식)
        - 딕셔너리 형태의 멀티모달 콘텐츠
        """
        gemini_parts = []
        
        for message in messages:
            content = message.content
            
            # 문자열인 경우 - 단순 텍스트
            if isinstance(content, str):
                role_prefix = ""
                if isinstance(message, SystemMessage):
                    role_prefix = "System: "
                elif isinstance(message, HumanMessage):
                    role_prefix = ""  # Human 메시지는 prefix 없이
                elif isinstance(message, AIMessage):
                    role_prefix = "Assistant: "
                gemini_parts.append(role_prefix + content)
            
            # 리스트인 경우 - 멀티모달 콘텐츠 (OpenAI 형식)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type", "")
                        
                        if item_type == "text":
                            gemini_parts.append(item.get("text", ""))
                        
                        elif item_type == "image_url":
                            image_url_data = item.get("image_url", {})
                            url = image_url_data.get("url", "") if isinstance(image_url_data, dict) else image_url_data
                            
                            # data URL 형식 처리 (data:image/png;base64,...)
                            if url.startswith("data:"):
                                image_obj = self._decode_data_url(url)
                                if image_obj:
                                    gemini_parts.append(image_obj)
                            else:
                                # 일반 URL - Gemini는 직접 URL을 지원하지 않으므로 경고
                                gemini_parts.append(f"[Image URL: {url}]")
                    
                    elif isinstance(item, str):
                        gemini_parts.append(item)
        
        return gemini_parts
    
    def _decode_data_url(self, data_url: str) -> Optional[Any]:
        """data URL을 PIL Image 또는 바이트로 디코딩"""
        if not PIL_AVAILABLE:
            # PIL이 없으면 바이트 딕셔너리로 반환
            try:
                header, data = data_url.split(",", 1)
                mime_type = header.split(":")[1].split(";")[0]
                image_bytes = base64.b64decode(data)
                return {"mime_type": mime_type, "data": image_bytes}
            except Exception:
                return None
        
        try:
            # data:image/png;base64,... 형식 파싱
            header, data = data_url.split(",", 1)
            image_bytes = base64.b64decode(data)
            image = Image.open(io.BytesIO(image_bytes))
            return image
        except Exception as e:
            return None
    
    def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """LangChain 메시지를 텍스트 프롬프트로 변환 (하위 호환성)"""
        prompt_parts = []
        
        for message in messages:
            if isinstance(message, SystemMessage):
                prompt_parts.append(f"System: {message.content}")
            elif isinstance(message, HumanMessage):
                if isinstance(message.content, str):
                    prompt_parts.append(f"Human: {message.content}")
                else:
                    # 멀티모달인 경우 텍스트만 추출
                    texts = [item.get("text", "") for item in message.content if isinstance(item, dict) and item.get("type") == "text"]
                    prompt_parts.append(f"Human: " + " ".join(texts))
            elif isinstance(message, AIMessage):
                prompt_parts.append(f"Assistant: {message.content}")
            else:
                prompt_parts.append(str(message.content))
        
        return "\n\n".join(prompt_parts)
    
    def _has_images(self, messages: List[BaseMessage]) -> bool:
        """메시지에 이미지가 포함되어 있는지 확인"""
        for message in messages:
            content = message.content
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        return True
        return False
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs
    ) -> ChatResult:
        """
        메시지 리스트로부터 응답 생성 (멀티모달 지원)
        
        Args:
            messages: 입력 메시지 리스트
            stop: 중지 시퀀스
            run_manager: 실행 매니저 (콜백용)
            **kwargs: 추가 생성 파라미터
            
        Returns:
            ChatResult 객체
        """
        # 이미지가 포함되어 있는지 확인
        has_images = self._has_images(messages)
        
        # 모델 파라미터 병합
        generation_params = {**self.model_kwargs, **kwargs}
        
        # API Pool을 통해 컨텐츠 생성
        try:
            if has_images:
                # 멀티모달 콘텐츠 - Gemini 형식으로 변환
                gemini_content = self._convert_messages_to_gemini_content(messages)
                response_text, usage_metadata = self.api_pool.generate_content(
                    gemini_content,
                    return_full_response=True,
                    **generation_params
                )
            else:
                # 텍스트만 있는 경우 - 단순 프롬프트
                prompt = self._convert_messages_to_prompt(messages)
                response_text, usage_metadata = self.api_pool.generate_content(
                    prompt,
                    return_full_response=True,
                    **generation_params
                )
            
            # 토큰 사용량 메타데이터 구성
            response_metadata = {}
            usage_metadata_dict = None
            if usage_metadata:
                usage_metadata_dict = {
                    "input_tokens": getattr(usage_metadata, 'prompt_token_count', 0),
                    "output_tokens": getattr(usage_metadata, 'candidates_token_count', 0),
                    "total_tokens": getattr(usage_metadata, 'total_token_count', 0),
                }
                response_metadata["usage"] = usage_metadata_dict
            
            # ChatResult 형식으로 변환
            message = AIMessage(
                content=response_text,
                response_metadata=response_metadata,
                usage_metadata=usage_metadata_dict,
            )
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
        """비동기 메시지 생성 (멀티모달 지원)"""
        # 이미지가 포함되어 있는지 확인
        has_images = self._has_images(messages)
        
        # 모델 파라미터 병합
        generation_params = {**self.model_kwargs, **kwargs}
        
        # API Pool을 통해 비동기로 컨텐츠 생성
        try:
            if has_images:
                # 멀티모달 콘텐츠 - Gemini 형식으로 변환
                gemini_content = self._convert_messages_to_gemini_content(messages)
                response_text = await self.api_pool.agenerate_content(
                    gemini_content,
                    **generation_params
                )
            else:
                # 텍스트만 있는 경우 - 단순 프롬프트
                prompt = self._convert_messages_to_prompt(messages)
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
