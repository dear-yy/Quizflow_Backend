# battle.consumers.py 

# 웹소켓 클라이언트와 텍스트 데이터 송수신 시에 Json 직렬화&역직렬화까지 모두 처리 
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import Battleroom, BattleArticle, BattleQuiz
from functions.battle.selectBattleArticle import extract_keywords, select_article # 랜덤 키워드 생성 & 아티클 반환
from functions.battle.summarization import summarize_article  # 요약 기능
from functions.battle.battleQuiz import generate_quiz_set
import json

# 배틀 설정 (퀴즈 & 아티클 생성)
class BattleSetupConsumer(JsonWebsocketConsumer):
    def connect(self):
        print("연결 중입니다.")
        self.player_1 = None  
        self.player_2 = None  
        self.battle_room = None  # 배틀룸 초기화
        self.article = None
        self.accept()

    def disconnect(self, close_code):
        print("연결을 중단합니다.")
        self.player_1 = None  
        self.player_2 = None  
        self.battle_room = None  # 배틀룸 초기화


    '''
    클라이언트로 부터 받을 메세지 형식     
    {"type":"", "player_role":""}
    '''
    def receive_json(self, content_dict, **kwargs): # 사용자 토큰 인증
        type = content_dict.get("type") # 인증 수행하고자 하는지 파악
        player_role = content_dict.get("player_role")  # "player_1" 또는 "player_2"

        if (self.player_1 is None or self.player_2 is None) and type=="auth": # 사용자 인증 전 상태
            token = content_dict.get("token")  # 클라이언트에서 보낸 토큰
            if not token:
                print("토큰이 제공되지 않았습니다. 정상적으로 토큰을 인증해주세요.")
                # self.close()
                return 
            
            try:
                user = Token.objects.get(key=token).user  # 토큰으로 사용자 인증
            except Token.DoesNotExist:
                print('유효하지 않은 토큰이므로, 연결을 중단합니다.')
                self.close()
                return
            
            # 플레이어 역할에 따라 사용자 지정
            if player_role == "player_1":
                if self.player_1 is None:
                    self.player_1 = user
                    print(f"{user}님이 player_1로 입장하였습니다.")
                elif self.player_1 != user:
                    print("이미 다른 플레이어 1이 설정되어 있습니다. 역할 설정 오류가 발생하여 연결을 중단합니다.")
                    self.close()
                    return
            elif player_role == "player_2":
                if self.player_2 is None:
                    self.player_2 = user
                    print(f"{user}님이 player_2로 입장하였습니다.")
                elif self.player_2 != user:
                    print("이미 다른 플레이어 2가 설정되어 있습니다. 역할 설정 오류가 발생하여 연결을 중단합니다.")
                    self.close()
                    return   
            else:
                print("잘못된 플레이어 역할입니다. 역할 설정 오류가 발생하여 연결을 중단합니다.")
                self.close()
                return
            
            # 두 명의 플레이어가 설정되었는지 확인
            if self.player_1 and self.player_2:
                self.setup_battle()  # 배틀룸 설정 시작

    def setup_battle(self):
        """ 두 명의 플레이어가 모두 인증되면 배틀룸을 조회하고 설정 """
        battle_room_id = self.scope["url_route"]["kwargs"]["battle_room_id"]
        
        try:
            self.battle_room = Battleroom.objects.get(pk=battle_room_id)
            # 설정 완료 메시지 전송
            print(f"배틀룸 {battle_room_id}의 아티클과 퀴즈를 생성중 입니다. 기다려주세요.")
            self.send_json({
                "type": "system",
                "message": "아티클을 반환중 입니다. 기다려주세요.",
            })
            
        except Battleroom.DoesNotExist:
            print("배틀룸을 찾을 수 없습니다. 연결 종료.")
            self.send_json({
                "type": "system",
                "message": "배틀룸을 찾을 수 없어 연결 종료합니다.",
            })
            self.close()
            return
        
        # 아티클 생성
        self.createBattleArticle()

        # 퀴즈 생성(아티클 기반)
        self.createBattleQuiz()
        
        # 설정 완료 메시지 전송 -> (프론트)클라이언트는 이 메세지 받으면, BattleConsumer 웹소켓으로 연결!
        print("배틀 설정이 완료") # 디버깅
        self.send_json({
            "type": "system",
            "message": "배틀 설정이 완료되었습니다. 이제 퀴즈를 시작하세요!"
        })

    def createBattleArticle(self):
        """ 아티클을 생성하는 로직 """
        # 랜덤 키워드 반환
        query = extract_keywords()

        # 아티클 반환
        recommended_article = select_article(self.player_1, self.player_2,  query)
        
        # 아티클 본문 요약
        recommended_article['body'] = summarize_article(recommended_article['body'])

        # 아티클 생성 및 Room 연결
        self.article = BattleArticle.objects.create(
            battleroom=self.battle_room,
            title=recommended_article['title'],
            body=recommended_article['body'],
            url=recommended_article['url']
        )
    
    def createBattleQuiz(self):
        """ 퀴즈 생성하는 로직"""
        # 생성 및 DB 저장 로직 추가 가능
        if not self.article:
            print("아티클이 설정되지 않았습니다. 퀴즈를 생성할 수 없습니다.")
            return
        print("아티클 기반 퀴즈를 생성 중...")

        # (객관식 퀴즈 + 서술형 퀴즈)를 한 번에 생성
        quiz_set = generate_quiz_set(self.article.body) # 딕셔너리 형태 반환

        # 생성된 퀴즈 세트 생성 여부 파악 
        if not quiz_set:
            print("퀴즈 세트를 생성하는데 실패했습니다.")
            return
        
        quiz_1 = quiz_set["multiple_choice_1"]["quiz"]
        quiz_1_ans = quiz_set["multiple_choice_1"]["answer"]

        quiz_2 = quiz_set["multiple_choice_2"]["quiz"]
        quiz_2_ans = quiz_set["multiple_choice_2"]["answer"]

        quiz_3 = quiz_set["descriptive"]["quiz"]
        quiz_3_ans = quiz_set["descriptive"]["answer"]

        # 퀴즈 DB 저장
        battle_quiz = BattleQuiz.objects.create(
            battle_article = self.article,
            quiz_1 = quiz_1,
            quiz_1_ans = quiz_1_ans,
            quiz_2 = quiz_2,
            quiz_2_ans = quiz_2_ans,
            quiz_3 = quiz_3,
            quiz_3_ans = quiz_3_ans
        )

        # 배틀룸의 stage 변경 코드 추가하기 [setup -> quiz_1]


    

# 개별 퀴즈 진행 # 반환값 형식 에러 수정하기
class BattleConsumer(JsonWebsocketConsumer):
    def connect(self):
        print("연결 중입니다.")
        self.user = None
        self.role = None # 본인이 player_1인지 player_2인지
        self.battle_room = None
        self.battle_quiz =  None
        self.accept()

    def disconnect(self, close_code):
        self.user = None
        self.role = None
        self.battle_quiz =  None
        self.battle_room = None
        print("연결을 중단합니다.")

    # def receive_json(self, content_dict, **kwargs):
        # 퀴즈 상태 quiz_1이 아닌 경우 -> 종료 

    #     action = content_dict.get("action")

    #     if action == "submit_answer":
    #         quiz_type = content_dict.get("quiz_type")
    #         quiz_number = content_dict.get("quiz_number")  # 퀴즈 번호 (1, 2, 3)
    #         answer = content_dict.get("answer")
    #         self.process_answer(quiz_type, quiz_number, answer)

    # def process_answer(self, quiz_type, quiz_number, answer):
    #     """답안 처리 로직"""
    #     # 객관식 퀴즈 답안 확인
    #     if quiz_type == "multiple_choice":
    #         quiz = BattleQuiz.objects.get(battleroom=self.battle_room)
    #         correct_answer = getattr(quiz, f"quiz_{quiz_number}_ans")

    #         is_correct = (answer == correct_answer)
    #         self.send_json({
    #             "type": "answer_feedback",
    #             "quiz_number": quiz_number,
    #             "result": "correct" if is_correct else "incorrect",
    #         })
        
    #     # 서술형 퀴즈 답안 평가
    #     elif quiz_type == "descriptive":
    #         quiz = BattleQuiz.objects.get(battleroom=self.battle_room)
    #         correct_answer = quiz.quiz_3_ans  # 서술형 퀴즈는 항상 quiz_3로 설정

    #         feedback = evaluate_descriptive_answer(answer, correct_answer) # return (오류 발생 여부, 평가 기준, 채점 피드백, 점수)
    #         self.send_json({
    #             "type": "answer_feedback",
    #             "quiz_number": quiz_number,
    #             "feedback": feedback,
    #         })

    # 퀴즈 모델 데이터 조회 함수 

    # 각 단계 별 처리 함수 
        

'''
self.role
    if 1번 플레이어:
        (now_stage_1 / end_date_1 / total_score_1) 필드 사용
    else 2번 플레이어:
        (now_stage_2 / end_date_2 / total_score_2) 필드 사용



stage [setup -> quiz_1 -> quiz_2 -> quiz_3 -> finish]

quiz_1 
    시스템(GPT) 퀴즈 1번 사용자(클라이언트)에게 전달 
    사용자(클라이언트) 퀴즈 1번 답변 시스템으로 전달 
    시스템(GPT) 채점 결과 사용자(클라이언트)에게 전달 
quiz_2
    ...동일...
quiz_3
    ...동일...
finish
    시스템이 사용자(클라이언트)에게 종료 메세지(총점) 전송 


채점 메세지 형식 
    - 정답입니다.(2점)
    - 오답입니다.(0점)
    - 피드백: ~~~ (n점)


종료 메세지 
    - 000님, 수고하셨습니다. 총 점수는 M점 입니다. 

'''