import os
import sys
import openai
import time
import json 
from django.conf import settings
from typing import Tuple, Dict

# Django 프로젝트 절대 경로로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # __file__ : 현재 경로
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myquiz.settings')

# 키 설정 
openai.api_key = settings.OPENAI_API_KEY 

def generate_quiz_set(article_summary) -> Dict:
    # 객관식 퀴즈 생성 
    quiz_1, ans_1 = generate_multiple_choice_quiz_with_check(article_summary, previous_quiz=None)
    quiz_2, ans_2 = generate_multiple_choice_quiz_with_check(article_summary, previous_quiz=quiz_1)

    # 서술형 퀴즈 생성
    quiz_3, ans_3 = generate_descriptive_quiz(article_summary)

    return {
        "multiple_choice_1": {"quiz": quiz_1, "answer": ans_1},
        "multiple_choice_2": {"quiz": quiz_2, "answer": ans_2},
        "descriptive": {"quiz": quiz_3, "answer": ans_3}
    }


'''
[객관식]
    generate_multiple_choice_quiz_with_check 
    check_answer
'''

# 객관식식 퀴즈 & 모범 답안 생성 -> return (퀴즈, 모범 답안)
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

    ## 아티클 요약: {summary}
    
    ## 출력 형식 
        문제: 문제 지문

        1. 1번 선택지 내용 
        2. 2번 선택지 내용 
        3. 3번 선택지 내용 
        4. 4번 선택지 내용 
        5. 5번 선택지 내용 
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


# 객관식 채점 -> return (오류 발생 여부, 채점 메세지, 점수)
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
    



'''
[서술형]
    generate_descriptive_quiz 
    evaluate_descriptive_answer
'''

# 서술형 퀴즈 & 모범 답안 생성 -> return (퀴즈, 모범 답안)
def generate_descriptive_quiz(article_summary) -> Tuple[str, str]:
    while True:
        try:
            # 아티클기반 퀴즈 생성을 위한 프롬프트
            prompt_quiz = f"""
            당신은 '서술형 퀴즈 생성기'입니다.
            당신의 목표는 아티클 기반 서술형 퀴즈 생성입니다. 
            서술형 퀴즈 생성기는 주어진 아티클을 기반으로 해당 아티클의 주제 요약 퀴즈를 한문제 출제하세요.
            ## 작업 순서
              1. 아티클 분석: 제공된 아티클의 내용을 분석하고 핵심 내용과 중요 포인트를 파악한다.
              2. 퀴즈 출제: 아티클의 주요 내용을 기반으로 해당 아티클의 주제 요약에 대한 퀴즈를 한문장으로 한 문제 출제한다.
            ## 주의사항
              - 항상 아티클의 내용을 기반으로 객관적인 문제를 출제하세요.
              - **한 개의 퀴즈만** 출제하세요.
        
            ## 출력 형식 
                문제: 문제 지문

            ## 아티클: {article_summary}
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

            # 모범 답안 생성을 위한 프롬프트 
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
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)


# 서술형 채점 -> return (오류 발생 여부, 평가 기준, 채점 피드백, 점수)
def evaluate_descriptive_answer(user_answer, quiz, model_answer)-> Tuple[bool, dict, dict, int]:
    """
    GPT를 사용하여 사용자 답변을 평가합니다.
    """
    # 오류 발생 여부
    fail = False
    evaluation_result = None
    
    prompt_evaluation = f"""
    당신은 '서술형 퀴즈 평가자'라는 역할을 맡게 됩니다. 서술형 퀴즈 평가자는 주어진 평가기준을 기반으로 사용자의 답변을 평가하여 점수를 도출하고 사용자 답변에 대한 피드백을 제공합니다.
    즉, 당신의 목표는 모범 답안 기반 사용자의 작성 답안을 정확하게 평가하고 사용자 답변에 대해 이해도 피드백을 생성하는 것입니다.
    아래는 사용자가 작성한 서술형 퀴즈 답변입니다. 또한 퀴즈와 모범 답안을 참고하여, 답변을 평가하고 점수를 도출하고 이해도에 대한 피드백을 1줄로 작성하세요.

    [퀴즈]: {quiz}
    [모범 답안]: {model_answer}
    [사용자 답변]: {user_answer}

    ##평가 기준:
    1) 모범 답안과 비교해서 사용자 답안이 핵심 내용을 포함했음 (2점 부여)
    2) 사용자 답안이 모범 답안에 들어간 단어를 하나라도 사용했음 (1점 부여)
    3) 사용자 답안이 모범 답안의 의도를 왜곡하지 않았고 객관성 유지했음 (1점 부여)
    4) 사용자 답안이 2문장 이내로 작성됐음 (1점 부여)
    5) 사용자 답안이 사실과 다른 내용을 포함하지 않았음 (1점 부여)

    점수를 각 기준에 따라 합산하여 총점(6점 만점)을 부여하고, 각 기준에 대한 이해도 피드백을 작성하세요.

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
        "understanding_feedback": "사용자의 이해도에 대한 피드백
      }}
    }}
    """

    while True:  # RateLimitError가 발생하면 재시도
        try:
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
            return fail, evaluation_result["criteria"], evaluation_result["feedback"] , evaluation_result["total_score"]

        except openai.error.RateLimitError:  
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)

        except UnicodeDecodeError as e:  # 유니코드 디코딩 오류 발생 시
            print(f"유니코드 디코딩 오류 발생: {e}") 
            fail = True
            break # 루프 종료

        except json.JSONDecodeError as e: # JSON 디코딩 오류 발생 시
            print(f"JSON 디코딩 오류 발생: {e}")
            print("GPT 응답:", evaluation_result)  # 응답 내용 확인
            fail = True
            break  #  루프 종료
    
    if not isinstance(evaluation_result["total_score"], int): # 정수가 아니면
        fail = True

    # 처리 실패시 
    evaluation_result = {
        "total_score": 0,
        "criteria": {
            "content_inclusion": "JSON 변환 오류로 평가 실패",
            "keyword_usage": "JSON 변환 오류로 평가 실패",
            "objective_representation": "JSON 변환 오류로 평가 실패",
            "length_limit": "JSON 변환 오류로 평가 실패",
            "fact_accuracy": "JSON 변환 오류로 평가 실패"
        },
        "feedback": {
            "understanding_feedback": "JSON 변환 오류로 이해도 피드백 생성 실패"
        }
    }
    return fail, evaluation_result["criteria"], evaluation_result["feedback"] , evaluation_result["total_score"]

