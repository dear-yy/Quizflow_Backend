import os
import sys
import openai
import time
from django.conf import settings
from typing import Tuple

# Django 프로젝트 절대 경로로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# 키 설정 
openai.api_key = settings.OPENAI_API_KEY 

'''
generate_descriptive_quiz_with_check
check_descriptive_answer
'''

def generate_descriptive_quiz_with_check(summary, previous_quiz=None) -> Tuple[str, str]:
    """
    기사 요약을 기반으로 서술형 문제를 생성하고, 정답을 반환합니다.
    두 번째 문제는 첫 번째 문제와 다르게 출제됩니다.
    """
    # 서술형 퀴즈 생성 프롬프트
    prompt_quiz = f"""
    당신은 '서술형 퀴즈 생성기'입니다.
    주어진 아티클 요약을 기반으로 서술형 문제를 작성하세요.
    
    ## 작업 순서
      1. 아티클 분석: 제공된 아티클 요약 내용을 분석하여 주요 내용을 파악합니다.
      2. 퀴즈 출제: 아티클 요약 내용을 기반으로 서술형 문제를 작성합니다.
    
    ## 퀴즈의 구성 내용은 매번 바뀌게 출력해야 합니다.
    ## 첫 번째 문제와 중복되지 않도록 해야 하며, 두 번째 문제는 완전히 다른 질문이어야 합니다.
    {f'단, 이전 문제와 동일한 문제를 출제하지 않도록 주의해주세요. 이전 문제: {previous_quiz}' if previous_quiz else ''}
    
    아티클 요약:
    {summary}
    서술형 문제:
    """
    while True:
        try:
            response_quiz = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 서술형 퀴즈 생성기입니다."},
                    {"role": "user", "content": prompt_quiz}
                ],
                max_tokens=300,
                temperature=0
            )
            quiz = response_quiz["choices"][0]["message"]["content"].strip()
            break
        except openai.error.RateLimitError:
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)
    
    # 정답 생성 프롬프트
    prompt_answer = f"""
    당신은 '정답 생성기'입니다.
    주어진 서술형 문제에 대한 정답을 작성하세요.
    
    ##주의사항
    정답은 아티클 요약문의 내용을 바탕으로 생성해야 합니다.
    
    아티클 요약:
    {summary}
    서술형 문제:
    {quiz}
    정답:
    """
    while True:
        try:
            response_answer = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 정답 생성기입니다."},
                    {"role": "user", "content": prompt_answer}
                ],
                max_tokens=300,
                temperature=0
            )
            correct_answer = response_answer["choices"][0]["message"]["content"].strip()
            break
        except openai.error.RateLimitError:
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)
    
    return quiz, correct_answer


def check_descriptive_answer(user_answer: str, correct_answer: str) -> Tuple[bool, str, int]:
    """
    사용자 답안과 정답을 비교하여 점수를 반환합니다.
    AI를 사용하여 유사도를 평가하고 점수를 부여합니다.
    """
    prompt_check = f"""
    당신은 '서술형 답안 채점기'입니다.
    사용자 답안을 정답과 비교하여 유사도를 평가하고 0~2점 사이의 점수를 부여하세요.
    
    ## 점수 기준
    - 2점: 정답과 매우 유사한 답변
    - 1점: 일부 유사하지만 핵심 내용이 부족한 답변
    - 0점: 정답과 무관한 답변
    
    정답:
    {correct_answer}
    
    사용자 답안:
    {user_answer}
    
    점수(숫자로만 입력):
    """
    while True:
        try:
            response_check = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 서술형 답안 채점기입니다."},
                    {"role": "user", "content": prompt_check}
                ],
                max_tokens=5,
                temperature=0
            )
            score_content = response_check["choices"][0]["message"]["content"].strip()
            break
        except openai.error.RateLimitError:
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)
    
    try:
        score = int(score_content)
        if score not in [0, 1, 2]:
            raise ValueError("Invalid score received.")
    except ValueError:
        print(f"오류: 점수를 추출할 수 없습니다. 응답 내용: {score_content}")
        score = 0
    
    feedback = "정답입니다!" if score == 2 else "부분 정답입니다." if score == 1 else "오답입니다."
    return False, feedback, score
