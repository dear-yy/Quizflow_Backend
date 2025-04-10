import os
import sys
import openai
import json  
import time
from django.conf import settings
from typing import Tuple

# Django 프로젝트 절대 경로로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myquiz.settings')

# 키 설정 
openai.api_key = settings.OPENAI_API_KEY 

'''
generate_descriptive_quiz 
evaluate_descriptive_answer
'''

def generate_descriptive_quiz(article_summary)-> Tuple[str, str]:
    fail_cnt = 0
    while fail_cnt<3:  # 최대 3번 재시도
        try:
            # 서술형 퀴즈 생성
            prompt_quiz = f"""
                당신은 '서술형 퀴즈 생성기'라는 역할을 맡게 됩니다. 당신의 목표는 아티클 기반 서술형 퀴즈 생성입니다.
                서술형 퀴즈 생성기는 주어진 아티클을 기반으로 해당 아티클의 주제 요약 퀴즈를 한문제 출제하세요.
                ## 작업 순서
                  1. 아티클 분석: 제공된 아티클의 내용을 분석하고 핵심 내용과 중요 포인트를 파악한다.
                  2. 퀴즈 출제: 아티클의 주요 내용을 기반으로 해당 아티클의 주제 요약에 대한 퀴즈를 한문장으로 한 문제 출제한다.
                ## 주의사항
                  - 항상 아티클의 내용을 기반으로 객관적인 문제를 출제하세요.
                  - 아티클에 존재하지 않은 정보는 퀴즈 출제에 반영하지 않습니다.
                  - **한 개의 퀴즈만** 출제하세요.
                ## 아티클: {article_summary}
                ## 출력 형식 
                    문제: 문제 지문
            """
            # Open API 호출
            response_quiz = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 서술형 퀴즈 생성기입니다."},
                    {"role": "user", "content": prompt_quiz}
                ],
                max_tokens=150,
                temperature=0
            )
            quiz = response_quiz["choices"][0]["message"]["content"].strip()


            # 모범 답안 생성
            prompt_answer = f"""
                당신은 '모범 답안 생성기'라는 역할을 맡게 됩니다.
                모범 답안 생성기는 주어진 아티클을 기반으로 주어진 퀴즈에 적합한 모범 답안을 한 개 작성하세요.
                ## 작업 순서
                  1. 아티클 분석: 제공된 아티클 내용을 분석하고 핵심 내용과 중요 포인트를 파악한다.
                  2. 퀴즈 문제 분석: 아티클을 기반으로 퀴즈 문제를 분석하여, 퀴즈 문제가 요구하는 핵심 내용을 파악한다. 
                  3. 모범 답안 생성: 분석 내용을 통해 아티클 기반으로 퀴즈에 대한  **한 개의 모범 답안**을 2줄로 생성한다.
                ## 주의사항
                  - 항상 아티클과 퀴즈 출제 내용을 기반으로 적절한 모범 답안을 출력하세요.
                  - **한 개의 모범 답안만** 작성하세요.
                ## 아티클: {article_summary}
                ## 퀴즈: {quiz}
                모범 답안:
            """
            # Open API 호출
            response_answer = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 모범 답안 생성기입니다."},
                    {"role": "user", "content": prompt_answer}
                ],
                max_tokens=150,
                temperature=0
            )
            model_answer = response_answer["choices"][0]["message"]["content"].strip()

            return quiz, model_answer

        except openai.error.RateLimitError:
            fail_cnt += 1  
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)



def evaluate_descriptive_answer(user_answer, quiz, model_answer)-> Tuple[bool, dict, dict, int]:
    # 오류 발생 여부
    fail = False
    evaluation_result = None
    
    prompt_evaluation = f"""
        당신은 '서술형 퀴즈 평가자'라는 역할을 맡게 됩니다.
        서술형 퀴즈 평가자는 주어진 평가기준을 기반으로 사용자의 답변을 평가하여 점수를 도출하고 사용자 답변에 대한 피드백을 제공합니다.
        즉, 당신의 목표는 모범 답안 기반 사용자의 작성 답안을 정확하게 평가하고 사용자 답변에 대해 이해도와 개선점이라는 피드백을 생성하는 것입니다.
        퀴즈와 모범 답안 정보를 참고하여, 퀴즈에 대한 사용자 답변을 평가하고 점수를 도출하고 개선점과 이해도에 대한 피드백을 작성하세요.

        [퀴즈]: {quiz}
        [모범 답안]: {model_answer}
        [사용자 답변]: {user_answer}

        ## 평가 기준:
            1) 모범 답안과 비교해서 사용자 답안이 핵심 내용을 포함했음 (2점 부여)
            2) 사용자 답안이 모범 답안에 들어간 단어를 하나라도 사용했음 (1점 부여)
            3) 사용자 답안이 모범 답안의 의도를 왜곡하지 않았고 객관성 유지했음 (1점 부여)
            4) 사용자 답안이 2문장 이내로 작성됐음 (1점 부여)
            5) 사용자 답안이 사실과 다른 내용을 포함하지 않았음 (1점 부여)

            점수를 각 기준에 따라 합산하여 총점(6점 만점)을 부여하세요.

        ##최종 출력 형식:
            {{
            "total_score": 0,
            "feedback": {{
            "understanding_feedback": "사용자 답변 기반 이해도에 대한 피드백",
            "improvement_feedback": "사용자 답변 기반 개선할 점에 대한 피드백"
            }}
        }}
    """

    fail_cnt = 0
    while fail_cnt < 3:  # 최대 3번 재시도
        try:
            fail = False

            # GPT 호출
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 서술형 퀴즈 평가자입니다."},
                    {"role": "user", "content": prompt_evaluation}
                ],
                max_tokens=500,
                temperature=0
            )

            # GPT 응답 추출
            evaluation_result = response["choices"][0]["message"]["content"].strip()

            # BOM 제거 및 UTF-8 처리
            evaluation_result = evaluation_result.lstrip('\ufeff')
            evaluation_result = evaluation_result.encode('utf-8').decode('utf-8')

            # JSON 변환
            evaluation_result = json.loads(evaluation_result)
            # 결과 반환
            return fail, evaluation_result["feedback"] , evaluation_result["total_score"]

        except openai.error.RateLimitError:  
            fail_cnt += 1
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)

        except UnicodeDecodeError as e:  # 유니코드 디코딩 오류 발생
            print(f"유니코드 디코딩 오류 발생: {e}") 
            fail = True
            break # 루프 종료

        except json.JSONDecodeError as e: # JSON 디코딩 오류 발생
            print(f"JSON 디코딩 오류 발생: {e}")
            print("GPT 응답:", evaluation_result)  # 응답 내용 확인
            fail = True
            break  #  루프 종료
    
    if not isinstance(evaluation_result["total_score"], int): # 정수 변환
        fail = True

    # 처리 실패시 
    if fail is True:
        evaluation_result = {
            "total_score": 0,
            "feedback": {
                "understanding_feedback": "JSON 변환 오류로 이해도 피드백 생성 실패",
                "improvement_feedback": "JSON 변환 오류로 개선점 피드백 생성 실패"
            }
        }

    return fail, evaluation_result["feedback"] , evaluation_result["total_score"]