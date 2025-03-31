# battle.consumers.py 

import time
import json
from django.utils.timezone import now # 시간 활성화
from asgiref.sync import async_to_sync # 비동기 그룹 메시지 전송을 동기 방식으로 변환
from channels.generic.websocket import JsonWebsocketConsumer # Json 직렬화&역직렬화(비동기)
from rest_framework.authtoken.models import Token
# 모델
from django.contrib.auth.models import User
from .models import Battleroom, BattleArticle, BattleQuiz
# 기능
from functions.battle.selectBattleArticle import extract_keywords, select_article 
from functions.battle.summarization import summarize_article
from functions.battle.battleQuiz import generate_quiz_cycle, check_answer, evaluate_descriptive_answer



'''
## 배틀 설정 ##
    퀴즈 & 아티클 생성

[클라이언트 -> 서버]
    인증 요청
    {"type":"auth", "token":"token"}

[서버 -> 클라이언트]
    진행 상황 보고 
    {"type":"system", "message":"message"}
    에러 보고
    {"type":"fail", "message":"message"}
'''


class BattleSetupConsumer(JsonWebsocketConsumer):
    def connect(self):
        print("연결 중입니다.") # 디버깅
        self.battle_room = None  
        self.article = None
        self.myrole = None

        # 배틀룸 조회 
        self.get_battleroom_id()

        # 그룹 추가 (같은 battle_room_id를 가진 사용자끼리 그룹화)
        if self.battle_room:
            self.group_name = f"battleroom_{self.battle_room.id}"
            async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)

        self.accept()


    def disconnect(self, close_code):
        print("연결을 중단합니다.") # 디버깅
        self.disconnect_battleroom()

        # 그룹에서 제거
        if self.battle_room:
            async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)
            self.battle_room = None  

    def receive_json(self, content_dict, **kwargs):
        type = content_dict.get("type") # 메세지 유형 파악(인증)

        # 두 사용자 인증 수행
        if ((self.battle_room.player_1_connected is False) or (self.battle_room.player_2_connected is False)) and type=="auth": 
            # 1. 토큰 인증
            token = content_dict.get("token") 
            if not token:
                self.send_json({"type":"fail", "message":"토큰이 제공되지 않았습니다. 정상적으로 토큰을 인증해주세요."})
                print("토큰이 제공되지 않았습니다. 정상적으로 토큰을 인증해주세요.") # 디버깅
                return 
            
            try: # 토큰으로 사용자 인증 & 사용자 정보 반환
                user = Token.objects.get(key=token).user  
            except Token.DoesNotExist:
                self.send_json({"type":"fail", "message":"유효하지 않은 토큰이므로, 연결을 중단합니다."})
                print('유효하지 않은 토큰이므로, 연결을 중단합니다.')
                self.close()
                return
            
            # 2. 플레이어 역할에 따라 사용자 지정
            if user.id == self.battle_room.player_1.id:
                self.myrole = 1
                if self.battle_room.player_1_connected is False:
                    self.connect_battleroom()
                    print(f"{user.profile.nickname}님이 player_1로 입장하였습니다.") # 디버깅
                else:
                    self.send_message("fail", "player_1은은 설정 완료된 플레이어입니다.")
                    print("player_1은 설정 완료된 플레이어입니다.") # 디버깅
            elif user.id == self.battle_room.player_2.id:
                self.myrole = 2
                if self.battle_room.player_2_connected is False:
                    self.connect_battleroom()
                    print(f"{user.profile.nickname}님이 player_2로 입장하였습니다.") # 디버깅
                else:
                   self.send_message("fail", "player_2는 설정 완료된 플레이어입니다.")
                   print("player_2는 설정 완료된 플레이어입니다.") # 디버깅
            else:
                self.send_message("fail","존재하지 않은 플레이어입니다. 승인되지 않은 사용자 접근이 발생하여 연결을 중단합니다.")
                print("존재하지 않은 플레이어입니다. 승인되지 않은 사용자 접근이 발생하여 연결을 중단합니다.") # 디버깅
                # 예외 처리 구현(해당 배틀룸 삭제)
                print("현재 플레이어", user) # 디버깅
                self.close()
                return
            
            # 두 명의 플레이어 모두 설정 완료
            if  (self.battle_room.player_1_connected is True) and (self.battle_room.player_2_connected is True):
                self.setup_battle()  # 배틀룸 설정 시작

    def get_battleroom_id(self):
        battle_room_id = self.scope["url_route"]["kwargs"]["battle_room_id"]
        
        try:
            self.battle_room = Battleroom.objects.get(pk=battle_room_id)
        except Battleroom.DoesNotExist:
            self.send_message("fail", "배틀룸을 찾을 수 없어 연결을 종료합니다.")
            print("배틀룸을 조회 실패. 연결 종료.") # 디버깅
            self.close()
            return
        
    def connect_battleroom(self):
        if self.myrole == 1:
            self.battle_room.player_1_connected = True
        elif self.myrole == 2:
            self.battle_room.player_2_connected = True
        
        self.battle_room.save()
        return 
    
    def disconnect_battleroom(self):
        if self.myrole == 1:
            self.battle_room.player_1_connected = False
        elif self.myrole == 2:
            self.battle_room.player_2_connected = False
        
        self.battle_room.save()
        return 

    def setup_battle(self):
        # 1. 아티클 생성
        self.createBattleArticle()

        # 2. 퀴즈 생성(아티클 기반)
        self.createBattleQuiz()
        
        # 3. 설정 완료 메시지 전송 -> (프론트)클라이언트는 이 메세지 받으면, BattleConsumer 웹소켓으로 연결!
        self.battle_room.start_date = now()
        self.battle_room.save()

        print("배틀 설정 완료") # 디버깅
        self.send_message("system", "설정 완료")
        

    def createBattleArticle(self):
        print("아티클과 퀴즈를 생성중") # 디버깅

        # 1. 랜덤 키워드 반환
        query = extract_keywords()
        
        # 2. 아티클 반환
        recommended_article = select_article(self.battle_room.player_1, self.battle_room.player_2,  query)

        # 3. 아티클 본문 요약
        recommended_article['body'] = summarize_article(recommended_article['body'])

        # 4. 아티클 정보 DB 저장 및 Room 연결
        self.article = BattleArticle.objects.create(
            battleroom=self.battle_room,
            title=recommended_article['title'],
            body=recommended_article['body'],
            url=recommended_article['url']
        )
    
    def createBattleQuiz(self):
        # 1. 아티클 존재 여부 확인
        if not self.article:
            self.send_message("fail", "아티클이 설정되지 않았습니다. 퀴즈를 생성할 수 없습니다.")
            print("아티클이 설정되지 않았습니다. 퀴즈를 생성할 수 없습니다.") # 디버깅
            # 예외 처리 구현
            return
        print("아티클 기반 퀴즈를 생성 중...") # 디버깅

        # 2. 퀴즈 한 사이클 생성
        quiz_cycle = generate_quiz_cycle(self.article.body) # dict 형태 반환

        # 3. 생성된 퀴즈 세트 생성 여부 파악 
        if not quiz_cycle:
            print("퀴즈 세트를 생성하는데 실패했습니다.") # 디버깅
            # 예외 처리 구현 
            return

        # 4. 생성 퀴즈 DB 저장
        BattleQuiz.objects.create(
            battleroom = self.battle_room, 
            battle_article = self.article,
            quiz_1 = quiz_cycle["multiple_choice_1"]["quiz"],
            quiz_1_ans = quiz_cycle["multiple_choice_1"]["answer"],
            quiz_2 = quiz_cycle["multiple_choice_2"]["quiz"],
            quiz_2_ans = quiz_cycle["multiple_choice_2"]["answer"],
            quiz_3 = quiz_cycle["descriptive"]["quiz"],
            quiz_3_ans = quiz_cycle["descriptive"]["answer"]
        )

    def send_message(self, msg_type, message):
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                "type": "chat_message", # 핸들러 메서드 이름
                "msg_type": msg_type,
                "message": message
            }
        )

    def chat_message(self, event): # 그룹메세지 핸들러 메서드 
        # self.channel_layer.group_send (self.group_name, ...)을 event로 잡아냄
        self.send_json({
            "type": event["msg_type"],
            "message": event["message"]
        })



    
'''
## 개별 퀴즈 진행 ##

[클라이언트 -> 서버]
    시작 메세지 
    {"type":"auth"}
[서버 -> 클라이언트]
    퀴즈 메세지 
    {"type":"user", "message":"quiz_ans"}
'''
# 반환값 형식 에러 수정하기
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

    def receive_json(self, content_dict, **kwargs):
        type = content_dict.get("type")
        
        # 배틀룸 입장
        if self.user is None and type=="auth": # 기본 세팅 전
            # 1. 사용자 조회 
            self.user = self.get_user()

            # 2. 배틀룸 조회
            self.battle_room = self.get_battleroom()
            
            # 3. 역할 추출
            self.role = self.get_player_role() # "player_n"
            print("role", self.role)
            # 4. 배틀 퀴즈 조회
            self.battle_quiz = self.battle_room.battle_quiz

            # 5. 배틀 퀴즈 진행 
            if self.role == "player_1":
                self.process_stage_player_1()
            elif self.role == "player_2": 
                self.process_stage_player_2()

        # 배틀룸 퀴즈 진행 중 (퀴즈 답변 전송)
        elif type=="user":  # 기본 세팅 후
            # 1. 사용자 답변 수신
            message_content = content_dict.get("message")

            # 2. 퀴즈 단계별 처리 
            if self.role == "player_1":
                self.process_stage_player_1(message_content)
            elif self.role == "player_2": 
                self.process_stage_player_2(message_content)




    # 사용자 조회 함수 
    def get_user(self) -> User | None: # 존재하면 인스턴스 반환, 없으면 None 반환 
        # 사용자 pk
        user_id = self.scope["url_route"]["kwargs"]["player_id"] # url captured value로서 player_id를 지정했었음

        # 사용자 조회
        user: User= None
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            print("사용자 조회에 실패하였습니다.")
            # 예외 처리 구현 
            pass
       
        # 조회한 사용자 객체 반환
        return user

    # 배틀룸 조회 함수 
    def get_battleroom(self) -> Battleroom | None: # 채팅방 존재하면 인스턴스 반환, 없으면 None 반환 
        # 배틀룸 pk 
        battleroom_id = self.scope["url_route"]["kwargs"]["battle_room_id"] # url captured value로서 battle_room_id를 지정했었음
        
        # 배틀룸 조회 
        battleroom: Battleroom = None
        try:
            battleroom = Battleroom.objects.get(pk=battleroom_id)
        except Battleroom.DoesNotExist: # 로그인 유저에 대해 채팅방을 못찾은 경우 
            print("존재하지 않은 배틀룸입니다.")
            # 예외 처리 구현
            pass
        
        # 조회한 채팅방 객체 반환
        return battleroom 
    
    def get_player_role(self) -> str:
        if self.user.id == self.battle_room.player_1.id:
            return "player_1"
        elif self.user.id == self.battle_room.player_2.id:
            return "player_2"
        else:
            print("존재하지 않은 플레이어입니다. 승인되지 않은 사용자 접근이 발생하였습니다.") # 디버깅
            # 예외 처리 구현
            return "fail"
       
       
    
    # 배틀 퀴즈 단계별 처리 함수
    def process_stage_player_1(self, message_content=""):
        send_message =  "" # 초기화

        if self.battle_room.now_stage_1 == "article": # 아티클 정보 메세지 전송
            print("--article--")
            article = self.battle_room.article.first() 
            # 예외 처리(아티클 정보 존재 여부) # UTF8 처리하기
            send_message = {"url":article.url, "title":article.title}
            self.battle_room.now_stage_1 = "quiz_1"

        elif self.battle_room.now_stage_1 == "quiz_1": # quiz_1 (문제) 메세지 전송 
            print("--quiz_1--")
            send_message = self.battle_quiz.quiz_1
            self.battle_room.now_stage_1 = "quiz_1_ans"
        elif self.battle_room.now_stage_1 == "quiz_1_ans":# quiz_1 (채점) 메세지 전송 
            print("--quiz_1_ans--")
            fail, send_message, score = check_answer(message_content, self.battle_quiz.quiz_1_ans)
            self.battle_room.total_score_1 += score
            if fail is False: # 성공한 경우만 
                self.battle_room.now_stage_1 = "quiz_2"
        
        elif self.battle_room.now_stage_1 == "quiz_2":# quiz_2 (문제) 메세지 전송
            print("--quiz_2--")
            send_message = self.battle_quiz.quiz_2
            self.battle_room.now_stage_1 = "quiz_2_ans"
        elif self.battle_room.now_stage_1 == "quiz_2_ans":# quiz_2 (채점) 메세지 전송
            print("--quiz_2_ans--")
            fail, send_message, score = check_answer(message_content, self.battle_quiz.quiz_2_ans)
            self.battle_room.total_score_1 += score
            if fail is False: # 성공한 경우만 
                self.battle_room.now_stage_1 = "quiz_3"

        elif self.battle_room.now_stage_1 == "quiz_3":# quiz_3 (문제) 메세지 전송 
            print("--quiz_3--")
            send_message = self.battle_quiz.quiz_3
            self.battle_room.now_stage_1 = "quiz_3_ans"
        elif self.battle_room.now_stage_1 == "quiz_3_ans":# quiz_3 (채점) 메세지 전송
            print("--quiz_3_ans--")
            fail, send_message, score = evaluate_descriptive_answer(message_content, self.battle_quiz.quiz_3, self.battle_quiz.quiz_3_ans)
            self.battle_room.total_score_1 += score
            send_message = send_message + f"({score}점)"
            if fail is False: # 성공한 경우만 
                self.battle_room.now_stage_1 = "finish"

        elif self.battle_room.now_stage_1 == "finish": # 종료 메세지 
            print("--배틀 종료--")
            send_message = f"{self.user.profile.nickname}님, 수고하셨습니다. 총 점수는 {self.battle_room.total_score_1}점 입니다."

            if self.battle_room.end_date_2 is not None: # 상대 플레이어가 배틀을 먼저 끝냄
                message_content = {"message":"두 플레이어 모두 배틀 퀴즈를 완료하여, 배틀 퀴즈를 종료합니다.", "player_1": True, "player_2":True, "my_role":1}
                self.battle_room.is_ended = True
            else: # 현재 플레이어가 배틀은 먼저 끝냄
                message_content = {"message":"상대 플레이어가 배틀 퀴즈를 완료하지 못했습니다. 잠시만 대기해주세요.", "player_1": True, "player_2":False, "my_role":1}

            self.battle_room.now_stage_1 = "end" # 최종 종료
            
        self.battle_room.save()
        self.send_json({"type":"user", "message":send_message , "is_gpt": True})
        if self.battle_room.now_stage_1 == "end": 
            # battle 종료
            self.send_json({"type":"user", "message_content": message_content, "is_gpt": True})
            self.close()

        if self.battle_room.now_stage_1 in ["quiz_1", "quiz_2", "quiz_3", "finish"]: # 직접 호출 필요 단계
            time.sleep(2)  # 2초 동안 대기
            self.process_stage_player_1()
        

    def process_stage_player_2(self, message_content=""):   
        send_message =  "" # 초기화

        if self.battle_room.now_stage_2 == "article": # 아티클 정보 메세지 전송
            print("--article--")
            article = self.battle_room.article.first() 
            # 예외 처리(아티클 정보 존재 여부) # UTF8 처리하기
            send_message = {"url":article.url, "title":article.title}
            self.battle_room.now_stage_2 = "quiz_1"

        elif self.battle_room.now_stage_2 == "quiz_1": # quiz_1 (문제) 메세지 전송 
            print("--quiz_1--")
            send_message = self.battle_quiz.quiz_1
            self.battle_room.now_stage_2 = "quiz_1_ans"
        elif self.battle_room.now_stage_2 == "quiz_1_ans":# quiz_1 (채점) 메세지 전송 
            print("--quiz_1_ans--")
            fail, send_message, score = check_answer(message_content, self.battle_quiz.quiz_1_ans)
            self.battle_room.total_score_2 += score
            if fail is False: # 성공한 경우만 
                self.battle_room.now_stage_2 = "quiz_2"
        
        elif self.battle_room.now_stage_2 == "quiz_2":# quiz_2 (문제) 메세지 전송
            print("--quiz_2--")
            send_message = self.battle_quiz.quiz_2
            self.battle_room.now_stage_2 = "quiz_2_ans"
        elif self.battle_room.now_stage_2 == "quiz_2_ans":# quiz_2 (채점) 메세지 전송
            print("--quiz_2_ans--")
            fail, send_message, score = check_answer(message_content, self.battle_quiz.quiz_2_ans)
            self.battle_room.total_score_2 += score
            if fail is False: # 성공한 경우만 
                self.battle_room.now_stage_2 = "quiz_3"

        elif self.battle_room.now_stage_2 == "quiz_3":# quiz_3 (문제) 메세지 전송 
            print("--quiz_3--")
            send_message = self.battle_quiz.quiz_3
            self.battle_room.now_stage_2 = "quiz_3_ans"
        elif self.battle_room.now_stage_2 == "quiz_3_ans":# quiz_3 (채점) 메세지 전송
            print("--quiz_3_ans--")
            fail, send_message, score = evaluate_descriptive_answer(message_content, self.battle_quiz.quiz_3, self.battle_quiz.quiz_3_ans)
            self.battle_room.total_score_2 += score
            send_message = send_message + f"({score}점)"
            if fail is False: # 성공한 경우만 
                self.battle_room.now_stage_2 = "finish"

        elif self.battle_room.now_stage_2 == "finish": # 종료 메세지 
            print("--배틀 종료--")
            send_message = f"{self.user.profile.nickname}님, 수고하셨습니다. 총 점수는 {self.battle_room.total_score_2}점 입니다."

            if self.battle_room.end_date_1 is not None: # 상대 플레이어가 배틀을 먼저 끝냄
                message_content = {"message":"두 플레이어 모두 배틀 퀴즈를 완료하여, 배틀 퀴즈를 종료합니다.", "player_1": True, "player_2":True, "my_role":2}
                self.battle_room.is_ended = True
            else: # 현재 플레이어가 배틀은 먼저 끝냄 
                message_content = {"message":"상대 플레이어가 배틀 퀴즈를 완료하지 못했습니다. 잠시만 대기해주세요.", "player_1": False, "player_2":True, "my_role":2}  
            
            self.battle_room.now_stage_2 = "end"
        
        self.battle_room.save()
        self.send_json({"type":"user", "message":send_message , "is_gpt": True})
        if self.battle_room.now_stage_2 == "end":
            self.send_json({"type":"user", "message_content": message_content, "is_gpt": True})
            self.close()

        if self.battle_room.now_stage_2 in ["quiz_1", "quiz_2", "quiz_3", "finish"]: # 직접 호출 필요 단계
            time.sleep(2)  # 2초 동안 대기
            self.process_stage_player_2()
            




'''

stage [article -> quiz_1 -> quiz_1_ans -> quiz_2 -> quiz_2_ans -> quiz_3 -> quiz_3_ans -> finish]

article
    시스템이 사용자(클라이언트)에게 아티클 정보 전달

quiz_n 
    시스템(GPT) 퀴즈 1번 사용자(클라이언트)에게 전달 
quiz_n_ans
    사용자(클라이언트) 퀴즈 1번 답변 시스템으로 전달 
    시스템(GPT) 채점 결과 사용자(클라이언트)에게 전달 

finish
    시스템이 사용자(클라이언트)에게 종료 메세지(총점) 전달


채점 메세지 형식 
    - 정답입니다.(2점)
    - 오답입니다.(0점)
    - 피드백: ~~~ (n점)

종료 메세지 
    - 000님, 수고하셨습니다. 총 점수는 M점 입니다. 

'''



