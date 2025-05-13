import sqlite3
from typing import List, Dict, Optional
from ..core.conversation_elements import Message
from ..models.conversation.analysis_io import (
    RealtimeAnalysisRequest,
    RealtimeAnalysisResponse
)
from ..services.session_services.realtime_sentimental_analysis import (
    RealtimeSentimentalAnalysisLLMOutput
)

EWMA_ALPHA = 0.15
DB_PATH = "conversation_history.db"

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    conn = _get_conn()
    c = conn.cursor()
    # 메시지 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            conversation_id TEXT,
            message_id INTEGER,
            role TEXT,
            content TEXT,
            PRIMARY KEY (conversation_id, message_id)
        )
    ''')
    # 점수 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            conversation_id TEXT PRIMARY KEY,
            partner_engagement REAL DEFAULT 0,
            my_engagement REAL DEFAULT 0,
            my_talk_share REAL DEFAULT 0,
            last_modified_message_id INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

_init_db()

def is_conversation_exists(conversation_id: str) -> bool:
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM messages WHERE conversation_id=? LIMIT 1", (conversation_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def is_message_exists(conversation_id: str, message: Message) -> bool:
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT 1 FROM messages WHERE conversation_id=? AND message_id=? AND role=? AND content=?",
        (conversation_id, message.message_id, message.role, message.content)
    )
    result = c.fetchone()
    conn.close()
    return result is not None

def init_conversation(conversation_id: str) -> None:
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO scores (conversation_id) VALUES (?)",
        (conversation_id,)
    )
    conn.commit()
    conn.close()

def delete_conversation(conversation_id: str) -> None:
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
    c.execute("DELETE FROM scores WHERE conversation_id=?", (conversation_id,))
    conn.commit()
    conn.close()

def update_message(conversation_id: str, message: Message) -> None:
    if is_message_exists(conversation_id, message):
        return
    
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (conversation_id, message_id, role, content) VALUES (?, ?, ?, ?)",
        (conversation_id, message.message_id, message.role, message.content)
    )
    conn.commit()
    conn.close()

def get_messages(conversation_id: str, n_window: int = 5) -> List[Message]:
    conn = _get_conn()
    c = conn.cursor()
    if n_window is None:
        c.execute(
            "SELECT message_id, role, content FROM messages WHERE conversation_id=? ORDER BY message_id ASC",
            (conversation_id,)
        )
    else:
        c.execute(
            "SELECT message_id, role, content FROM messages WHERE conversation_id=? ORDER BY message_id DESC LIMIT ?",
            (conversation_id, n_window)
        )
    rows = c.fetchall()
    conn.close()
    # 최신순 정렬로 가져온 경우 역순으로 정렬하여 오름차순으로 반환
    if n_window is not None:
        rows = list(reversed(rows))
    messages = [
        Message(message_id=row["message_id"], role=row["role"], content=row["content"])
        for row in rows
    ]
    return messages

def update_realtime_analysis(
    conversation_id: str,
    message: Message,
    sentiment_analysis: RealtimeSentimentalAnalysisLLMOutput,
) -> RealtimeAnalysisResponse:
    
    conn = _get_conn()
    c = conn.cursor()
    # 점수 가져오기
    c.execute(
        "SELECT partner_engagement, my_engagement, my_talk_share FROM scores WHERE conversation_id=?",
        (conversation_id,)
    )
    row = c.fetchone()
    if row is None:
        partner_engagement = 0
        my_engagement = 0
        my_talk_share = 0
    else:
        partner_engagement = row["partner_engagement"]
        my_engagement = row["my_engagement"]
        my_talk_share = row["my_talk_share"]

    # 감정 점수 변환
    if sentiment_analysis.final_answer == "긍정":
        cur_score = 1
    elif sentiment_analysis.final_answer == "중립":
        cur_score = 0.5
    elif sentiment_analysis.final_answer == "부정":
        cur_score = 0
    else:
        cur_score = 0.5

    # EWMA 적용
    if message.role == "파트너":
        partner_engagement = EWMA_ALPHA * cur_score + (1 - EWMA_ALPHA) * partner_engagement
    if message.role == "나":
        my_engagement = EWMA_ALPHA * cur_score + (1 - EWMA_ALPHA) * my_engagement

    # talk share 계산
    c.execute(
        "SELECT content, role FROM messages WHERE conversation_id=?",
        (conversation_id,)
    )
    all_msgs = c.fetchall()
    total_length = sum(len(row["content"]) for row in all_msgs)
    my_length = sum(len(row["content"]) for row in all_msgs if row["role"] == "나")
    if total_length > 0:
        my_talk_share = my_length / total_length
    else:
        my_talk_share = 0

    # 점수 업데이트
    c.execute(
        '''INSERT INTO scores (conversation_id, partner_engagement, my_engagement, my_talk_share, last_modified_message_id)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(conversation_id) DO UPDATE SET
               partner_engagement=excluded.partner_engagement,
               my_engagement=excluded.my_engagement,
               my_talk_share=excluded.my_talk_share,
               last_modified_message_id=excluded.last_modified_message_id
        ''',
        (
            conversation_id,
            partner_engagement,
            my_engagement,
            my_talk_share,
            message.message_id
        )
    )
    conn.commit()
    conn.close()
    return RealtimeAnalysisResponse(
        partner_engagement_score=partner_engagement,
        my_engagement_score=my_engagement,
        my_talk_share=my_talk_share
    )

def get_realtime_analysis(conversation_id: str) -> RealtimeAnalysisResponse:
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT partner_engagement, my_engagement, my_talk_share FROM scores WHERE conversation_id=?",
        (conversation_id,)
    )
    row = c.fetchone()
    conn.close()
    if row is None:
        return RealtimeAnalysisResponse(
            partner_engagement_score=0,
            my_engagement_score=0,
            my_talk_share=0
        )
    return RealtimeAnalysisResponse(
        partner_engagement_score=row["partner_engagement"],
        my_engagement_score=row["my_engagement"],
        my_talk_share=row["my_talk_share"]
    )
    

def _register_example_data():
    # 예시 대화 데이터
    conversation_id = "test_conversation_id"
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
    partner_engagement = 0.85
    my_engagement = 0.75
    my_talk_share = 0.65
    last_modified_message_id = 40

    # 대화 및 점수 등록
    conn = _get_conn()
    c = conn.cursor()
    # 메시지 등록
    for msg in messages:
        c.execute(
            "INSERT OR IGNORE INTO messages (conversation_id, message_id, role, content) VALUES (?, ?, ?, ?)",
            (conversation_id, msg.message_id, msg.role, msg.content)
        )
    # 점수 등록
    c.execute(
        '''INSERT OR REPLACE INTO scores (conversation_id, partner_engagement, my_engagement, my_talk_share, last_modified_message_id)
           VALUES (?, ?, ?, ?, ?)''',
        (conversation_id, partner_engagement, my_engagement, my_talk_share, last_modified_message_id)
    )
    conn.commit()
    conn.close()

_register_example_data()