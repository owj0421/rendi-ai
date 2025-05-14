import sqlite3
from typing import List, Dict, Optional
from ..core.conversation_elements import Message
from ..models import conversation_models
from ..services.session_services.realtime_sentimental_analysis import (
    RealtimeSentimentalAnalysisLLMOutput
)

EWMA_ALPHA = 0.25
DB_PATH = "conversation_history.db"

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    conn = _get_conn()
    c = conn.cursor()
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


def update_realtime_analysis(
    conversation_id: str,
    message: Message,
    sentiment_analysis: RealtimeSentimentalAnalysisLLMOutput,
) -> conversation_models.RealtimeAnalysis:
    
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
    cur_score = sentiment_analysis.score

    # EWMA 적용
    if message.role == "파트너":
        if partner_engagement == 0:
            partner_engagement = cur_score
        else:
            partner_engagement = EWMA_ALPHA * cur_score + (1 - EWMA_ALPHA) * partner_engagement
    if message.role == "나":
        if my_engagement == 0:
            my_engagement = cur_score
        else:
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
    
    return True

def get_realtime_analysis(conversation_id: str) -> conversation_models.RealtimeAnalysis:
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT partner_engagement, my_engagement, my_talk_share FROM scores WHERE conversation_id=?",
        (conversation_id,)
    )
    row = c.fetchone()
    conn.close()
    if row is None:
        return conversation_models.RealtimeAnalysis(
            partner_engagement_score=0,
            my_engagement_score=0,
            my_talk_share=0
        )
    return conversation_models.RealtimeAnalysis(
        partner_engagement_score=row["partner_engagement"],
        my_engagement_score=row["my_engagement"],
        my_talk_share=row["my_talk_share"]
    )