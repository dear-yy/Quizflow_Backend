# battle.consumers.py 

# 웹소켓 클라이언트와 텍스트 데이터 송수신 시에 Json 직렬화&역직렬화까지 모두 처리 
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import Battleroom, BattleArticle, BattleQuiz
from functions.battle.selectBattleArticle import extract_keywords, select_article # 랜덤 키워드 생성 & 아티클 반환
from functions.battle.summarization import summarize_article  # 요약 기능
from functions.battle.battleQuiz import generate_quiz_set, generate_descriptive_quiz, check_answers, evaluate_descriptive_answer
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
        
        # 설정 완료 메시지 전송
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

        # generate_quiz_set 호출 (객관식 퀴즈 + 서술형 퀴즈를 한 번에 생성)
        quiz_set = generate_quiz_set(self.article)

        # 퀴즈 DB 저장
        BattleQuiz.objects.create(
            battleroom=self.battle_room,
            article=self.article,
            multiple_choice=quiz_set['multiple_choice'],
            descriptive=quiz_set['descriptive']
        )

        # 퀴즈 전송
        self.send_json({
            "type": "quiz",
            "multiple_choice": quiz_set['multiple_choice'],
            "descriptive": quiz_set['descriptive'],
        })

    

# 개별 퀴즈 진행
class BattleConsumer(JsonWebsocketConsumer):
    def connect(self):
        print("연결 중입니다.")
        self.user = None
        self.role = None # 본인이 player_1인지 player_2인지
        self.battle_room = None
        self.accept()

    def disconnect(self, close_code):
        self.user = None
        self.role = None
        self.battle_room = None
        print("연결을 중단합니다.")

    def receive_json(self, content_dict, **kwargs):
        action = content_dict.get("action")

        if action == "submit_answer":
            quiz_type = content_dict.get("quiz_type")
            answer = content_dict.get("answer")
            self.process_answer(quiz_type, answer)

    def process_answer(self, quiz_type, answer):
        """답안 처리 로직"""
        if quiz_type == "multiple_choice":
            # 객관식 퀴즈 답안 확인
            is_correct = check_answers(answer)
            self.send_json({
                "type": "answer_feedback",
                "result": "correct" if is_correct else "incorrect",
            })
        elif quiz_type == "descriptive":
            # 서술형 퀴즈 답안 평가
            feedback = evaluate_descriptive_answer(answer)
            self.send_json({
                "type": "answer_feedback",
                "feedback": feedback,
            })
        