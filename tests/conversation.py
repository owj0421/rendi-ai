# PYTHONPATH=. pytest -s tests/conversation.py

import sys
import os
import pytest
import logging
from httpx import AsyncClient

from app.main import app
from app.services.elements import Message

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_conversation_full_flow():
    conversation_id = "test-conv-001"
    messages = [
        Message(message_id=0, role="나", content="안녕하세요. 저는 오원준이라고 해요."),
        Message(message_id=1, role="파트너", content="안녕하세요. 강유민입니다."),
        Message(message_id=2, role="나", content="아... 네. 진짜 어색하네요. 이런 자리 처음이라."),
        Message(message_id=3, role="파트너", content="저도요. 오면서도 계속 고민했어요, 무슨 얘기해야 하나."),
        Message(message_id=4, role="나", content="근데 생각보다 편하게 말씀하시네요."),
        Message(message_id=5, role="파트너", content="아, 그런가요? 사실 안 그런 척하는 중이에요."),
        Message(message_id=6, role="나", content="저도 되게 긴장했는데, 조금씩 풀리는 것 같아요."),
        Message(message_id=7, role="파트너", content="다행이에요. 저도 말하다 보니까 좀 나아졌어요."),
        Message(message_id=8, role="나", content="혹시... 지금 무슨 일 하고 계세요?"),
        Message(message_id=9, role="파트너", content="저는 디자인 쪽 일해요. UX 디자이너로 회사 다니고 있어요."),
        Message(message_id=10, role="나", content="오, 디자인. 멋있다. 저는 앱 개발 쪽 하고 있어요."),
        Message(message_id=11, role="파트너", content="앗, 그러면 우리 약간 협업하는 느낌이네요."),
        Message(message_id=12, role="나", content="그러게요. 개발자랑 디자이너면 싸울 일도 많다던데요."),
        Message(message_id=13, role="파트너", content="하하, 그런 말 있죠. 저는 그래도 협업 스타일 좋은 편이에요."),
        Message(message_id=14, role="나", content="오, 좋네요. 저도 웬만하면 맞춰주는 스타일이에요."),
        Message(message_id=15, role="파트너", content="그럼 딱 맞는 조합인가요?"),
        Message(message_id=16, role="나", content="글쎄요, 아직은 잘 모르겠는데, 느낌은 괜찮은 것 같아요."),
        Message(message_id=17, role="파트너", content="저도 그렇게 생각해요. 말이 잘 통하는 편인 것 같고."),
        Message(message_id=18, role="나", content="혹시 요즘 뭐에 빠져 계세요?"),
        Message(message_id=19, role="파트너", content="음... 최근엔 전시 보러 다니는 거에 좀 빠졌어요."),
        Message(message_id=20, role="나", content="오, 전시. 저도 미술관 가는 거 좋아해요."),
        Message(message_id=21, role="파트너", content="진짜요? 의외인데요. 되게 IT 쪽 분들은 잘 안 가는 줄 알았어요."),
        Message(message_id=22, role="나", content="사실 혼자 가는 건 잘 안 하는데, 누가 같이 가면 좋아요."),
        Message(message_id=23, role="파트너", content="그런 거 저도 비슷해요. 같이 가면 얘기도 나눌 수 있고."),
        Message(message_id=24, role="나", content="그럼 다음에 혹시 시간 되시면... 같이 가실래요?"),
        Message(message_id=25, role="파트너", content="좋죠. 전 좋습니다."),
        Message(message_id=26, role="나", content="오, 그럼 벌써 약속 하나 잡은 거네요."),
        Message(message_id=27, role="파트너", content="그러네요. 이런 거 빠른 거 좋아요."),
        Message(message_id=28, role="나", content="혹시 커피는 좋아하세요?"),
        Message(message_id=29, role="파트너", content="진짜 좋아해요. 하루에 한두 잔은 꼭 마셔요."),
        Message(message_id=30, role="나", content="저도요. 요즘은 드립 커피에 빠졌어요."),
        Message(message_id=31, role="파트너", content="오, 직접 내려 드시는 건가요?"),
        Message(message_id=32, role="나", content="네, 기계까지는 없고 그냥 핸드드립으로요."),
        Message(message_id=33, role="파트너", content="대단하네요. 저는 그냥 아아만 시켜 마셔요."),
        Message(message_id=34, role="나", content="아아는 진리죠. 사계절 내내요?"),
        Message(message_id=35, role="파트너", content="그럼요. 겨울에도 아아죠."),
        Message(message_id=36, role="나", content="저랑 취향 진짜 비슷하신 것 같아요."),
        Message(message_id=37, role="파트너", content="그러게요. 이래서 대화가 잘 되는 건가 봐요."),
        Message(message_id=38, role="나", content="음... 혹시 MBTI 여쭤봐도 될까요?"),
        Message(message_id=39, role="파트너", content="네, 저 INFP요. 원준님은요?"),
        Message(message_id=40, role="나", content="저는 INTJ요. 약간 대칭이네요."),
    ]
    # messages.extend([
    #     Message(message_id=41, role="파트너", content="근데 사실 저는 MBTI 같은 거 별로 안 믿어요."),
    #     Message(message_id=42, role="나", content="아, 네... 그냥 가볍게 여쭤본 거였어요."),
    #     Message(message_id=43, role="파트너", content="요즘 다들 너무 MBTI에 집착하는 것 같아서 좀 피곤하더라고요."),
    #     Message(message_id=44, role="나", content="아... 그런 의도는 아니었는데, 불편하셨다면 죄송해요."),
    #     Message(message_id=45, role="파트너", content="아니에요. 그냥 제 생각을 말한 거예요."),
    #     Message(message_id=46, role="나", content="분위기가 좀 어색해진 것 같네요."),
    #     Message(message_id=47, role="파트너", content="네, 솔직히 좀 불편해졌어요."),
    #     Message(message_id=48, role="나", content="제가 뭔가 실수한 것 같아서 신경 쓰이네요."),
    #     Message(message_id=49, role="파트너", content="괜찮아요. 그냥 대화가 잘 안 맞는 것 같아요."),
    #     Message(message_id=50, role="나", content="이런 자리, 역시 저랑은 안 맞는 것 같아요."),
    #     Message(message_id=51, role="파트너", content="저도 사실 이런 만남 별로 안 좋아해요."),
    #     Message(message_id=52, role="나", content="계속 대화가 겉도는 느낌이에요."),
    #     Message(message_id=53, role="파트너", content="저도 공감이 잘 안 되는 것 같아요."),
    #     Message(message_id=54, role="나", content="혹시 제가 너무 질문만 한 건 아니었나요?"),
    #     Message(message_id=55, role="파트너", content="아니요, 그냥 서로 관심사가 많이 다른 것 같아요."),
    #     Message(message_id=56, role="나", content="오늘 대화가 기대만큼 즐겁진 않네요."),
    #     Message(message_id=57, role="파트너", content="저도 좀 피곤해서 그런지 집중이 잘 안 돼요."),
    #     Message(message_id=58, role="나", content="이쯤에서 대화를 마치는 게 좋을까요?"),
    #     Message(message_id=59, role="파트너", content="네, 저도 그게 좋을 것 같아요."),
    #     Message(message_id=60, role="나", content="알겠습니다. 오늘 시간 내주셔서 감사합니다."),
    #     Message(message_id=61, role="파트너", content="네, 수고하셨어요."),
    # ])
    advice_id = "advice_1"  # 실제 존재하는 advice_id로 교체 필요

    async with AsyncClient(base_url="http://127.0.0.1:8000/api/v1") as ac:        
        # 1. 대화 세션 초기화
        resp = await ac.post(f"/conversation/{conversation_id}")
        logger.info(f"Init conversation")
        logger.info(f"↳ Response: {resp.status_code} {resp.text}")
        assert resp.status_code == 201

        # 2. 여러 번 메시지 추가
        for msg in messages:
            resp = await ac.post(
            f"/conversation/{conversation_id}/messages",
            json={"message": msg.dict()}
            )
            logger.info(f"Add message: {msg.content}")
            logger.info(f"↳ Response: {resp.status_code} {resp.text}")
            assert resp.status_code == 200

            # 메시지 추가 후 실시간 메모 호출
            resp = await ac.post(f"/conversation/{conversation_id}/realtime-memory")
            logger.info(f"Call realtime-memory after message")
            logger.info(f"↳ Response: {resp.status_code} {resp.text}")
            # partner_memory = memo_resp.json().get("partner_memory")['content']
            # logger.info("Realtime Memo")
            
            # if isinstance(partner_memory, dict):
            #     for k, v in partner_memory.items():
            #         logger.info(f"  {k}: {v if v else '-'}")
            # else:
            #     logger.info(f"↳ {partner_memory}")
            assert resp.status_code == 200
            
        
        # 3. 실시간 분석 결과 조회
        resp = await ac.post(f"/conversation/{conversation_id}/breaktime-advice/recommendation")
        logger.info(f"Realtime analysis")
        logger.info(f"↳ Response: {resp.status_code} {resp.text}")
        assert resp.status_code == 200

        # 4. 조언 상세 조회 (advice_id는 실제 존재하는 값이어야 함)
        resp = await ac.post(f"/conversation/{conversation_id}/breaktime-advice/{advice_id}")
        logger.info(f"Breaktime advice")
        logger.info(f"↳ Response: {resp.status_code} {resp.text}")
        assert resp.status_code == 200
        
        # 5. 최종 리포트
        resp = await ac.post(f"/conversation/{conversation_id}/final-report")
        logger.info(f"Final report")
        logger.info(f"↳ Response: {resp.status_code} {resp.text}")
        assert resp.status_code == 200

        # 6. 대화 세션 삭제
        resp = await ac.delete(f"/conversation/{conversation_id}")
        logger.info(f"Delete conversation")
        logger.info(f"↳ Response: {resp.status_code} {resp.text}")
        assert resp.status_code == 200

        # 종료
        logger.info("Test completed successfully.")
