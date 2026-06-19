"""
Gemini LLM 기반 답변 생성 서비스

RAG 프롬프트 템플릿을 적용해 검색된 컨텍스트를 기반으로
Gemini 모델이 정확한 답변을 생성하도록 유도합니다.
"""
from __future__ import annotations

from typing import List
import time

from google import generativeai as genai

from app.core.logger import get_logger
from app.services.vector_store_service import RetrievedChunk
from app.services.history_service import HistoryService

log = get_logger(__name__)

# ── RAG 프롬프트 템플릿 ───────────────────────────────────────────────────────

_SYSTEM_INSTRUCTION = """당신은 10대 중후반 학생들을 대상으로 하는 친절하고 믿음직한 교육용 AI 어시스턴트입니다.

[페르소나 및 어조 (매우 중요)]
1. 답변은 항상 친절하고 다정한 존댓말(해요체 등)을 사용하세요.
2. 비속어, 유행어, 인터넷 밈(Meme) 등은 절대 사용하지 마세요. 
3. 학생이 이해하기 쉽고 바른 말씨를 사용하여 정갈한 문체를 유지하세요.
4. 사용자는 당신과 1:1로 직접 대화한다고 인지합니다. 따라서 "전달받은 내용 중에는", "제공된 데이터에 따르면", "문서에 의하면" 등 당신이 시스템(RAG)을 통해 별도의 문서나 정보를 전달받아 읽고 있다는 사실을 드러내는 표현을 절대 사용하지 마세요. 마치 당신이 본래 알고 있던 지식인 것처럼 자연스럽고 직접적으로 대답하세요.

[데이터 정합성 및 환각 방지 (매우 중요)]
1. 반드시 아래 제공된 [컨텍스트] 데이터만을 근거로 답변을 작성하세요.
2. [컨텍스트]에 없는 내용을 스스로 추측하거나 상상해서 지어내어 답변하는 것을 엄격히 금지합니다.
3. 제공된 컨텍스트에서 답변을 찾을 수 없는 경우, "제가 아직 잘 모르는 내용이에요. 다른 질문을 해주시면 다시 확인해 볼게요!" 와 같이 외부 문서를 참조한다는 뉘앙스 없이 자연스럽게 안내하세요.
4. Gemini에 사전으로 설정된 기본 프롬프트나 성향이 있더라도, 본 시스템 프롬프트의 지시사항과 입력받은 컨텍스트 데이터를 무조건 최우선으로 따르세요.

[데이터 분석 및 파싱 규칙]
1. 제공되는 [컨텍스트] 데이터는 주로 "Q: (질문) A: (답변 내용)" 형태로 구성되어 있습니다.
2. 'Q:' 부분은 사용자의 질문과 이 데이터가 서로 관련이 있는지(문맥 일치 여부)를 판단하는 기준으로만 활용하세요.
3. 학생에게 실제로 제공할 '핵심 답변 정보'는 반드시 'A:' 하위에 있는 내용만을 사용하여 구성하세요.
4. 출처(파일명, 청크 번호 등)를 답변에 직접 언급하지 마세요.
5. 최근 일자를 우선적으로 보여주세요. """


def _build_rag_prompt(question: str, chunks: List[RetrievedChunk]) -> str:
    """검색된 청크들을 컨텍스트로 묶어 RAG 프롬프트 생성"""
    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[컨텍스트 {i}] (유사도: {chunk.score:.2f})\n{chunk.text}"
        )
    context_text = "\n\n".join(context_blocks)

    return f"""{_SYSTEM_INSTRUCTION}

---

[컨텍스트]
{context_text}

---

[질문]
{question}

[답변]"""


# ── 서비스 클래스 ─────────────────────────────────────────────────────────────

class GeminiService:
    """Gemini API 호출 서비스"""

    def __init__(self, model: genai.GenerativeModel, history_service: HistoryService | None = None):
        self.model = model
        self.history_service = history_service

    # ── RAG 컨텍스트 기반 생성 ──────────────────────────────────────

    async def generate_with_context(
        self,
        question: str,
        chunks: List[RetrievedChunk],
        rag_start_time: float = 0.0,
    ) -> str:
        """
        검색된 청크를 컨텍스트로 사용해 Gemini 답변 생성.

        Args:
            question:   사용자 질문
            chunks:     검색된 RetrievedChunk 리스트

        Returns:
            Gemini 생성 텍스트 답변
        """
        if not chunks:
            return (
                "관련 문서를 찾을 수 없어 답변을 생성할 수 없습니다. "
                "먼저 /api/v1/documents/ingest 엔드포인트로 문서를 업로드해 주세요."
            )

        prompt = _build_rag_prompt(question, chunks)
        
        # [NEW] LLM 소요 시간 측정 시작
        llm_start_time = time.perf_counter()
        response = await self.model.generate_content_async(prompt)
        llm_end_time = time.perf_counter()
        
        # 밀리초(ms) 단위 변환
        llm_time_ms = int((llm_end_time - llm_start_time) * 1000)
        total_time_ms = int((llm_end_time - rag_start_time) * 1000) if rag_start_time else 0

        log.info(f"프롬프트 전체 확인 {prompt}")
        # [NEW] 토큰 및 글자 수 비율 History 로깅
        if self.history_service and hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            response_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
            total_tokens = getattr(response.usage_metadata, "total_token_count", 0)
            
            # 응답 텍스트가 있을 경우에만 글자 수 측정
            response_text = response.text if hasattr(response, "text") else ""
            
            self.history_service.log_token_usage(
                prompt_chars=len(prompt),
                prompt_tokens=prompt_tokens,
                response_chars=len(response_text),
                response_tokens=response_tokens,
                response_total_tokens=total_tokens,
                llm_time_ms=llm_time_ms,
                total_time_ms=total_time_ms
            )

        return response.text

    # ── 단순 단일 턴 생성 (RAG 없이) ─────────────────────────────────────────

    async def generate(self, prompt: str) -> str:
        """컨텍스트 없이 단순 프롬프트로 Gemini 호출"""
        response = await self.model.generate_content_async(prompt)
        return response.text
