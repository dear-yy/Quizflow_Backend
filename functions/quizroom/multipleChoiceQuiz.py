import os
import sys
import openai
import time
from django.conf import settings
from typing import Tuple

# Django 프로젝트 절대 경로로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # __file__ : 현재 경로
# DJANGO_SETTINGS_MODULE 환경 변수를 설정하여 Django 설정을 로드합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# 키 설정 
openai.api_key = settings.OPENAI_API_KEY 

'''
generate_multiple_choice_quiz_with_check
check_answer
'''

def generate_multiple_choice_quiz_with_check(summary, previous_quiz=None) -> Tuple[str, int]:
    """
    기사 요약을 기반으로 객관식 문제를 생성하고, 정답을 반환합니다.
    두 번째 문제는 첫 번째 문제와 다르게 출제됩니다.
    """
    # 객관식 퀴즈 생성 프롬프트
    prompt_quiz = f"""
    당신은 '객관식 퀴즈 생성기'라는 역할을 맡게 됩니다.
    주어진 아티클 요약을 기반으로 5지 선다형 객관식 문제를 작성하세요.

    ## 작업 순서
      1. 아티클 분석: 제공된 아티클 요약 내용을 분석하여 주요 내용을 파악합니다.
      2. 퀴즈 출제: 아티클 요약 내용을 기반으로 한 개의 객관식 문제를 작성합니다.
      3. 선택지 작성: 정답 포함, 총 5개의 선택지를 작성합니다.

    ## 퀴즈의 구성 내용은 매번 바뀌게 출력한다. 문제1과 문제2가 같으면 절대 안 됩니다.
    ## 첫 번째 문제와 중복되지 않도록 해야 하며, 두 번째 문제는 완전히 다른 질문이어야 합니다.

    {f"단, 이전 문제와 동일한 문제를 출제하지 않도록 주의해주세요. 이전 문제: {previous_quiz}" if previous_quiz else ""}

    ## 정답을 화면에 절대 출력하지 않도록 합니다.

    아티클 요약:
    {summary}
    객관식 문제:
    """
    while True:  # RateLimitError가 발생하면 재시도
        try:
            # Open API 호출
            response_quiz = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 객관식 퀴즈 생성기입니다."},
                    {"role": "user", "content": prompt_quiz}
                ],
                max_tokens=300,
                temperature=0
            )
            quiz = response_quiz["choices"][0]["message"]["content"].strip()
            break  # 정상적으로 응답을 받으면 루프 종료
        except openai.error.RateLimitError:  
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)  # 40초 대기 후 재시도

    # 정답 생성 프롬프트
    prompt_answer = f"""
        당신은 '정답 생성기'라는 역할을 맡게 됩니다.
        주어진 객관식 문제에서 올바른 정답을 선택하고, 그 번호를 숫자로만 반환하세요.
        ##주의사항
        퀴즈를 분석후, 정답은 아티클 요약문의 내용을 바탕으로 생성해야한다.
        ##예시
        1, 2, 3, 4, 5 (단, 숫자만 반환해야 하며, 다른 텍스트는 포함하지 마세요)
        아티클 요약문:
            {summary}
        객관식 문제:
            {quiz}
        정답:
    """
    while True:   # RateLimitError가 발생하면 재시도
        try:
            # Open API 호출
            response_answer = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 정답 생성기입니다."},
                    {"role": "user", "content": prompt_answer}
                ],
                max_tokens=5,
                temperature=0
            )
            answer_content = response_answer["choices"][0]["message"]["content"].strip()
            break  # 정상적으로 응답을 받으면 루프 종료
        except openai.error.RateLimitError:  
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)  # 40초 대기 후 재시도

    # 정답을 추출할 때 '정답을 숫자로'와 같은 잘못된 값이 나오지 않도록 처리
    try:
        correct_answer = int(answer_content)  # 실제로 정답 번호가 숫자로 반환되는지 확인
    except ValueError:
        print(f"오류: 정답을 추출할 수 없습니다. 응답 내용: {answer_content}")
        correct_answer = None  # 정답이 없으면 None 반환

    return quiz, correct_answer



#채점
def check_answer(user_answer, correct_answer) -> Tuple[bool, str, int]:
    """
    사용자 답안과 정답을 비교하여 점수를 반환합니다.
    정답 시 2점, 오답 시 0점을 반환합니다.
    """
    if user_answer.isdigit():  # 사용자 입력이 숫자만 포함된 경우
        user_answer_int = int(user_answer) # 문자열을 정수로 변환
        if 1 <= user_answer_int <= 5: # 1과 5 사이의 정수
            # 채점
            if user_answer_int == correct_answer: # 정답
                return False, "축하합니다. 정답입니다.", 2
            else: #오답
                return False, f"오답입니다. 정답은 {correct_answer}입니다.", 0
        else:
            return True, "범위가 유효하지 않습니다. 다시 입력해주세요.", 0
    else: # 사용자 입력이 숫자가 아닐 경우 처리
        return True, "입력 형식에 맞게 다시 입력해주세요.", 0