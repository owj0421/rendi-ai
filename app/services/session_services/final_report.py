from datetime import datetime
from typing import Dict, Optional, List, Literal

from pydantic import BaseModel, Field

from ..elements import Message
from ...utils.prompt_utils import load_prompt
from ...core import clients, logger
import asyncio
import json

from . import (
    memory as memory_service,
    score as score_service,
)

log = logger.get_logger(__name__)

# === Constants ===

N_MESSAGES = 128
N_MESSAGES_OVERLAP = 32

# === Models ===


# === PartnerMemoryFinalSummarizer ===

class PartnerMemoryFinalSummarizer:
    PROMPT_NAME = "final_report/partner_memory_final_summarizer"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-mini"

    @classmethod
    def _generate_prompt(cls, conversation_memory: memory_service.ConversationMemory) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER).format(
                categories=memory_service.PARTNER_MEMORY_CATEGORIES,
            )
        }
        user_message = {
            "role": "user",
            "content": '\n---\n'.join([
                conversation_memory.prompt_partner_memory()
            ])
        }

        return [system_message, user_message]
    
    @classmethod
    async def do(cls, conversation_memory: memory_service.ConversationMemory):
        prompt_messages = cls._generate_prompt(conversation_memory)

        response = await clients.async_openai_client.chat.completions.create(
            messages=prompt_messages,
            model=cls.LLM_MODEL,
            response_format={"type": "json_object"}
        )
        response_json = response.choices[0].message.content
        response_dict = json.loads(response_json)
        response_data = memory_service.PartnerMemory(content=response_dict)
        
        return response_data
    
    

# === ConversationScorerFinalSummarizer ===
class ConversationScorerFinalSummarizer:
    pass

# 상대방이 부정적인 반응을 한 횟수
# 상대방이 긍정적인 반응을 한 횟수
    
# === Final Report Generation ===
    
async def write_final_report_pipeline(
    conversation_memory: memory_service.ConversationMemory,
    conversation_scorer: Optional[score_service.ConversationScorer] = None,
) -> None:
    final_report = ""
    
    # Generate the final report
    final_report += "### 📝 파트너에 대해 알게 된 내용을 정리해드릴게요!\n"
    partner_memory = await PartnerMemoryFinalSummarizer.do(conversation_memory=conversation_memory)
    final_report += memory_service.partner_memory_to_str(partner_memory, add_prefix=False)
    
    return final_report
    
if __name__ == "__main__":
    conv_memory = memory_service.ConversationMemory()
    
    conv_memory.partner_memory = memory_service.PartnerMemory(
        content={
            "취미/관심사": [
                "최근 전시 보러 다니는 것에 빠져 있음.",
                "주말마다 등산을 즐김.",
                "요가와 필라테스를 꾸준히 함.",
                "독서 모임에 참여하고 있음.",
                "사진 찍는 것을 좋아함.",
                "새로운 카페 탐방을 즐김.",
                "음악 페스티벌에 자주 감.",
                "요리와 베이킹에 관심이 많음.",
                "영화 감상과 리뷰 쓰기를 즐김.",
                "플로리스트 클래스에 다녀본 경험이 있음."
            ],
            "고민": [
                "일과 삶의 균형을 맞추는 것이 어려움.",
                "장기적인 커리어 방향에 대한 고민이 있음.",
                "새로운 인간관계를 맺는 것이 쉽지 않음.",
                "최근 건강 관리에 신경을 쓰고 있음.",
                "시간 관리가 잘 안 되어 스트레스를 느낌.",
                "자기계발에 대한 압박감을 느낌.",
                "가족과의 소통이 줄어든 것에 대해 걱정함.",
                "경제적 독립에 대한 고민이 있음.",
                "친구들과의 관계가 예전 같지 않아 고민임.",
                "미래에 대한漠然한 불안감이 있음."
            ],
            "가족/친구": [
                "부모님과는 주 1회 이상 통화함.",
                "여동생과 사이가 매우 좋음.",
                "가족 여행을 자주 다녔음.",
                "친구들과는 주로 카톡으로 연락함.",
                "대학 동기들과 매년 모임을 가짐.",
                "어릴 때부터 친한 친구가 있음.",
                "가족 모두가 반려동물을 좋아함.",
                "친구들과 취미를 함께 즐김.",
                "가족과의 대화에서 솔직함을 중요시함.",
                "친구들과의 약속을 소중히 여김."
            ],
            "직업/학업": [
                "강유민은 UX 디자이너로 일하고 있음.",
                "협업 스타일이 좋은 편임.",
                "현재 스타트업에서 근무 중임.",
                "프로젝트 리더 경험이 있음.",
                "디자인 관련 자격증을 보유함.",
                "신입사원 멘토 역할을 맡은 적 있음.",
                "업무 효율화를 위해 다양한 툴을 사용함.",
                "사용자 인터뷰를 자주 진행함.",
                "팀 내에서 소통이 원활함.",
                "업계 트렌드에 관심이 많음."
            ],
            "성격/가치관": [
                "이름은 강유민입니다.",
                "처음 만남에서 대화 주제에 대해 고민하는 신중한 성격을 가지고 있음.",
                "솔직하고 직설적인 편임.",
                "새로운 도전을 두려워하지 않음.",
                "타인의 의견을 존중함.",
                "책임감이 강함.",
                "작은 일에도 감사함을 느낌.",
                "자기 반성이 빠름.",
                "공정함과 정의로움을 중요하게 생각함.",
                "유머 감각이 있음."
            ],
            "이상형/연애관": [
                "서로의 취미를 존중하는 사람을 선호함.",
                "대화가 잘 통하는 상대를 원함.",
                "신뢰를 가장 중요하게 생각함.",
                "자유로운 연애를 선호함.",
                "서로 성장할 수 있는 관계를 지향함.",
                "작은 배려를 잘하는 사람에게 끌림.",
                "감정 표현이 솔직한 사람을 좋아함.",
                "장기적인 관계를 선호함.",
                "취미가 비슷한 사람에게 호감이 감.",
                "서로의 공간을 존중하는 연애를 원함."
            ],
            "생활습관": [
                "하루에 한두 잔 정도 커피를 꼭 마시는 편임.",
                "아침형 인간임.",
                "주 3회 이상 운동을 함.",
                "일찍 자고 일찍 일어남.",
                "식단 관리를 신경 씀.",
                "주말에는 집에서 휴식을 취함.",
                "계획적으로 일정을 관리함.",
                "정리정돈을 잘하는 편임.",
                "매일 일기를 씀.",
                "퇴근 후 산책을 즐김."
            ]
        }
    )
    
    async def main():
        response = await write_final_report_pipeline(conv_memory)
        print(response)

    asyncio.run(main())