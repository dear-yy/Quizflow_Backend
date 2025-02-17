import os
import sys
import openai
import time
import json 
from django.conf import settings
from typing import Tuple, List

# Django 프로젝트 절대 경로로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # __file__ : 현재 경로
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myquiz.settings')

# 키 설정 
openai.api_key = settings.OPENAI_API_KEY 

def generate_quiz_set(article_summary) -> Tuple[List[dict], dict]:
    while True:
        try:
            # 객관식 퀴즈 생성
            prompt_mcq = f"""
            당신은 '객관식 퀴즈 생성기'입니다. 주어진 아티클 요약약을 기반으로 객관식 퀴즈를 2문제 출제하세요.
            각 문제는 보기 5개를 포함해야 하며, 정답을 명확하게 지정하세요.
            두 번째 문제는 첫 번째 문제와 다르게 출제됩니다.
            
            ## 작업 순서
            1. 아티클 분석: 제공된 아티클 요약 내용을 분석하여 주요 내용을 파악합니다.
            2. 퀴즈 출제: 아티클 요약 내용을 기반으로 한 개의 객관식 문제를 작성합니다.
            3. 선택지 작성: 정답 포함, 총 5개의 선택지를 작성합니다.

             ## 정답을 화면에 절대 출력하지 않도록 합니다.
            
            아티클: {article_summary}
            """
            
            response_mcq = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 객관식 퀴즈 생성기입니다."},
                    {"role": "user", "content": prompt_mcq}
                ],
                max_tokens=500,
                temperature=0
            )
            mcq_list = json.loads(response_mcq["choices"][0]["message"]["content"].strip())

            # 서술형 퀴즈 생성
            quiz, model_answer = generate_descriptive_quiz(article_summary)
            
            return mcq_list, {"quiz": quiz, "answer": model_answer}
        
        except openai.error.RateLimitError:
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)

def generate_descriptive_quiz(article_summary) -> Tuple[str, str]:
    while True:
        try:
            prompt_quiz = f"""
            당신은 '서술형 퀴즈 생성기'입니다.
            주어진 아티클을 기반으로 해당 아티클의 주제 요약 퀴즈를 한문제 출제하세요.
            ## 작업 순서
              1. 아티클 분석: 제공된 아티클의 내용을 분석하고 핵심 내용과 중요 포인트를 파악한다.
              2. 퀴즈 출제: 아티클의 주요 내용을 기반으로 해당 아티클의 주제 요약에 대한 퀴즈를 한문장으로 한 문제 출제한다.
            ## 주의사항
              - 항상 아티클의 내용을 기반으로 객관적인 문제를 출제하세요.
              - **한 개의 퀴즈만** 출제하세요.
            
            아티클: {article_summary}
            퀴즈:
            """
            
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

            prompt_answer = f"""
            당신은 '모범 답안 생성기'라는 역할을 맡게 됩니다. 모범 답안 생성기는 주어진 아티클을 기반으로 주어진 퀴즈 적합한 한 개의 모범 답안을 한 개 작성하세요.
            ## 작업 순서
              1. 아티클과 퀴즈 분석: 제공된 아티클과 퀴즈에 내용을 분석한다.
              2. 모범 답안 생성: 주어진 아티클 기반으로 퀴즈에 대한  **한 개의 모범 답안**을  모범 답안을 2줄로 생성한다.
            ## 주의사항
              - 항상 아티클과 퀴즈 출제 내용을 기반으로 적절한 모범 답안을 출력하세요.
              - **한 개의 모범 답안만** 작성하세요.
            
            아티클: {article_summary}
            퀴즈: {quiz}
            모범 답안:
            """
            
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
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)

def check_answers(user_answers, mcq_list, descriptive_answer) -> Tuple[List[bool], Tuple[bool, dict, dict, int]]:
    if len(user_answers) < 3:
        return [False, False, False], (False, {}, {}, 0)  # 모든 문제를 다 풀기 전까지 정답 공개 금지
    
    mcq_results = [user_answers[i] == mcq_list[i]["correct_answer"] for i in range(2)]
    descriptive_result = evaluate_descriptive_answer(user_answers[2], descriptive_answer["quiz"], descriptive_answer["answer"])
    return mcq_results + [descriptive_result[0]], descriptive_result

def evaluate_descriptive_answer(user_answer, quiz, model_answer) -> Tuple[bool, dict, dict, int]:
    while True:
        try:
            prompt_evaluation = f"""
            당신은 '서술형 퀴즈 평가자'라는 역할을 맡게 됩니다. 서술형 퀴즈 평가자는 주어진 평가기준을 기반으로 사용자의 답변을 평가하여 점수를 도출하고 사용자 답변에 대한 피드백을 제공합니다.
            즉, 당신의 목표는 모범 답안 기반 사용자의 작성 답안을 정확하게 평가하고 사용자 답변에 대해 이해도와 개선점이라는 피드백을 생성하는 것입니다.
            퀴즈와 모범 답안을 참고하여, 답변을 평가하고 점수를 도출하고 개선점과 이해도에 대한 피드백을 작성하세요.
            
            [퀴즈]: {quiz}
            [모범 답안]: {model_answer}
            [사용자 답변]: {user_answer}

            ##평가 기준:
            1) 모범 답안과 비교해서 사용자 답안이 핵심 내용을 포함했음 (2점 부여)
            2) 사용자 답안이 모범 답안에 들어간 단어를 하나라도 사용했음 (1점 부여)
            3) 사용자 답안이 모범 답안의 의도를 왜곡하지 않았고 객관성 유지했음 (1점 부여)
            4) 사용자 답안이 2문장 이내로 작성됐음 (1점 부여)
            5) 사용자 답안이 사실과 다른 내용을 포함하지 않았음 (1점 부여)

            점수를 각 기준에 따라 합산하여 총점(6점 만점)을 부여하고, 각 기준에 대한 이해도 피드백과 개선점 피드백을 작성하세요.

            ##최종 출력 형식:
            {{
                "total_score": 0,
                "criteria": {{
                "content_inclusion": "핵심 내용 포함에 대한 피드백",
                "keyword_usage": "키워드 사용에 대한 피드백",
                "objective_representation": "의도 왜곡에 대한 피드백",
                "length_limit": "2문장 제한에 대한 피드백",
                "fact_accuracy": "사실성 평가에 대한 피드백"
                 }},
                "feedback": {{
                "understanding_feedback": "사용자의 이해도에 대한 피드백",
                "improvement_feedback": "사용자가 개선할 점에 대한 피드백"
                }}
            }}
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 서술형 퀴즈 평가자입니다."},
                    {"role": "user", "content": prompt_evaluation}
                ],
                max_tokens=500,
                temperature=0
            )
            
            evaluation_result = json.loads(response["choices"][0]["message"]["content"].strip())
            return evaluation_result["correct"], evaluation_result["criteria"], evaluation_result["feedback"], evaluation_result["total_score"]
        
        except openai.error.RateLimitError:
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)
        except json.JSONDecodeError:
            return False, {}, {}, 0