# from typing import Dict, List, Literal
# from dataclasses import dataclass
# import asyncio
# from pydantic import BaseModel, Field
# from collections import Counter, defaultdict

# from ...core import (
#     conversation_elements,
#     clients,
#     config,
# )
# from ...models.conversation import (
#     analysis_io,
#     search_io
# )
# from ...prompts.loader import (
#     load_prompt
# )

# # 쿼리 분류: 대화 내용에 대한 질문 / Web 검색이 필요한 질문
# class QueryClassifierLLMOutput(BaseModel):
#     final_answer: Literal["Conversation", "Web"]
    
    
# class QueryClassifier():
#     PROMPT_NAME = "context_aware_search/query_classifier"
#     PROMPT_VER = 1
#     LLM_RESPONSE_FORMAT = QueryClassifierLLMOutput

#     @classmethod
#     def _generate_prompt(
#         cls,
#         query: str
#     ) -> List[Dict[str, str]]:
#         system_message = {
#             "role": "system",
#             "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
#         }
#         user_message = {
#             "role": "user",
#             "content": f"Query: {query}\n\nPlease classify the query as either 'Conversation' or 'Web'."
#         }

#         return [system_message, user_message]

#     @classmethod
#     async def do(
#         cls,
#         query: str,
#         n_consistency: int = 5
#     ) -> analysis_io.SentimentalAnalysisResponse | str:
#         prompt_messages = cls._generate_prompt(query)

#         async def single_run():
#             response = await clients.async_openai_client.beta.chat.completions.parse(
#                 messages=prompt_messages,
#                 model="gpt-4.1-nano",
#                 response_format=cls.LLM_RESPONSE_FORMAT,
#                 temperature=0.0,
#             )
#             response = response.choices[0].message

#             if hasattr(response, "refusal") and response.refusal:
#                 return response.refusal
#             else:
#                 return response.parsed

#         results = await asyncio.gather(*(single_run() for _ in range(n_consistency)))

#         final_answers = [
#             r.final_answer for r in results if isinstance(r, QueryClassifierLLMOutput)
#         ]

#         if not final_answers:
#             return results[0] if results else "No response"

#         most_common = max(set(final_answers), key=final_answers.count)
        
#         return search_io.QueryClassifierOutput(
#             final_answer=most_common
#         )


# # Web 검색이 필요한 질문일 경우... 현재 정보 + 대화 내용 기반 쿼리 Reformulation
# class QueryRewriterLLMOutput(BaseModel):
#     final_answer: str
    

# class QueryRewriter():
#     PROMPT_NAME = "context_aware_search/query_rewriter"
#     PROMPT_VER = 1
#     LLM_RESPONSE_FORMAT = QueryRewriterLLMOutput

#     @classmethod
#     def _generate_prompt(
#         cls,
#         query: str,
#         messages: List[conversation_elements.Message],
#         extra_info: Dict[str, str] = None
#     ) -> List[Dict[str, str]]:
#         system_message = {
#             "role": "system",
#             "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
#         }

#         messages_str = "\n".join([message.to_prompt() for message in messages])

#         extra_info_str = ""
#         if extra_info:
#             extra_info_items = "\n".join([f"- {k}: {v}" for k, v in extra_info.items()])
#             extra_info_str = f"\n소개팅 관련 추가 정보:\n{extra_info_items}\n"

#         user_message = {
#             "role": "user",
#             "content": (
#                 f"사용자 원래 검색어: \"{query}\"\n\n"
#                 f"대화 내용:\n{messages_str}\n"
#                 f"{extra_info_str}"
#                 "소개팅 상황을 고려하여 검색어를 사용자 의도에 맞게 더 자연스럽고 적절하게 바꿔주세요."
#             )
#         }

#         return [system_message, user_message]

#     @classmethod
#     async def do(
#         cls,
#         query: str,
#         messages: List[conversation_elements.Message],
#         extra_info: Dict[str, str] = None
#     ) -> search_io.QueryRewriterOutput | str:
        
#         prompt_messages = cls._generate_prompt(query, messages, extra_info)
        
#         response = await clients.async_openai_client.beta.chat.completions.parse(
#             messages=prompt_messages,
#             model="gpt-4.1-mini",
#             response_format=cls.LLM_RESPONSE_FORMAT,
#             temperature=0.0,
#         )
#         response = response.choices[0].message

#         if hasattr(response, "refusal") and response.refusal:
#             return response.refusal
#         else:
#             return search_io.QueryRewriterOutput(
#                 final_answer=response.parsed.final_answer
#             )


# class SearchFromConversation():
#     pass


# class SearchFromWeb():
#     pass