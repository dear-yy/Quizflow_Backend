# quiz_room.consumers.py 

# 웹소켓 클라이언트와 텍스트 데이터 송수신 시에 Json 직렬화&역직렬화까지 모두 처리 
from channels.generic.websocket import JsonWebsocketConsumer
# import openai
from typing import Tuple, Dict
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from quiz_room.models import Quizroom, QuizroomMessage, Article, MultipleChoiceQuiz,  DescriptiveQuiz
from functions.selectArticle import get_keywords_from_feedback, select_article
from functions.summarization import summarize_article
import json


# 서버측 웹소켓 연결 처리 
class QuizroomConsumer(JsonWebsocketConsumer):
    def connect(self):
        print("연결 중입니다.")
        self.user = None # 인증 전이므로, None으로 초기화
        self.quizroom = None # 조회 전이므로, None으로 초기화
        self.now_stage = None  # 퀴즈 진행 상태 초기화
        self.accept()

    def disconnect(self, close_code):
        print("연결을 중단합니다.")
        self.user = None  # 사용자 정보 초기화
        self.quizroom = None # 방 정보 초기화
        self.now_stage = None  # 퀴즈 진행 상태 초기화
        

    def receive_json(self, content_dict, **kwargs):
        print(f'{content_dict}')
        type = content_dict.get("type")
        if self.user is None and type=="auth": # 사용자 인증 전 상태
            # 1. 토큰 검사
            token = content_dict.get("token") # 클라이언트에서 보낸 토큰 가져오기
            if token : # 토큰 입력 존재
                try: 
                    self.user = Token.objects.get(key=token).user # 토큰으로 사용자 인증
                    print(f'{self.user}의 토큰이 존재합니다')
                    print("~웹소켓에 연결되었습니다~ 잠시만 기다려 주세요 ~") 
                except Token.DoesNotExist: # 유효하지 않은 토큰
                    print(f'유효하지 않은 토큰이므로 연결이 종료됩니다...')
                    self.close()
                    return 
            else: # 토큰 입력 없음
                print("토큰이 제공되지 않아 연결이 종료됩니다...")
                self.close()
                return 

            # 2. 채팅방 조회
            self.quizroom = self.get_quizroom() # 채팅방 조회
            if self.quizroom is None: 
                print("조회할 수 없는 방이므로 연결이 종료됩니다...")
                self.close() # 존재하지 않는 방이면 연결 거부
                return 
            else: 
                print(f"[{self.user}의 방]") # 해당 방으로 연결

            # 3. 퀴즈 진행 상태 검사, cnt 값 검증
            if self.quizroom.cnt >= 3:
                print("완료된 퀴즈룸 입니다. 연결을 종료합니다.")
                self.send_json({"error": "최대 퀴즈 수를 초과했습니다." })
                self.close()
                return
            
            # 4. 퀴즈 진행 상태 복원
            self.now_stage = self.quizroom.now_stage
            print(f'{self.now_stage}부터 시작합니다.')

            # 5. 퀴즈 진행(gpt 답변 단계에서 중단된 경우)
            if self.now_stage in ["article", "quiz_1", "quiz_2", "quiz_3"]:
                self.process_stage(None)
            
        elif type=="user":  # 이미 인증된 사용자인 경우
            print(f"📩 {self.user}의 메시지: {content_dict}")
            message_content = content_dict.get("message")
            
            # 5. 메세지 처리
            self.process_stage(message_content)



    # 채팅방 조회
    def get_quizroom(self) -> Quizroom | None: # 채팅방 존재하면 인스턴스 반환, 없으면 None 반환 
        quizroom: Quizroom = None # 초기값을 None으로 설정하여, 방 못찾으면 그대로 반환 

        # 퀴즈룸 pk 
            # routing.py에서 url captured value로서 quizroom_id를 지정했었음
        quizroom_id = self.scope["url_route"]["kwargs"]["quizroom_id"]

        # 사용자 소유 방인지 
        print(f"사용자 {self.user}의 {quizroom_id}번 방 조회... ")    
        try:
            quizroom = Quizroom.objects.get(pk=quizroom_id, user=self.user)
        except Quizroom.DoesNotExist: # 로그인 유저에 대해 채팅방을 못찾은 경우 
            print("현재 조회중인 방은 사용자의 방이 아닙니다.")
            pass
       
        # 조회한 채팅방 객체 반환
        return quizroom 
    


    def process_stage(self, message_content):
        # stages = ["feedback", "article", "quiz_1", "user_ans_1", "quiz_2", "user_ans_2", "quiz_3", "user_ans_3"]
        fail = True # 처리 성공하면 False로 
        receive_message = None  # 사용자(클라이언트 -> 서버)
        send_message = None     # gpt (서버 -> 클라이언트) 

        if self.quizroom.cnt < 3: # 퀴즈 진행중
            if self.now_stage == "feedback":
                fail, receive_message = self.process_feedback(message_content)
                if fail: # 처리 실패
                    send_message = receive_message
                else: # 처리 성공
                    self.now_stage = "article" # stage 상태 변경
            elif self.now_stage == "article":
                fail, send_message = self.process_article()
                if fail==False: # 처리 성공
                    self.now_stage ="quiz_1" # stage 상태 변경
            elif self.now_stage == "quiz_1":
                print("퀴즈 시작~")
                fail, send_message = self.self.process_quiz_1()
                if fail==False: # 처리 성공
                    self.now_stage ="user_ans_1" # stage 상태 변경
            # elif self.now_stage == "user_ans_1":
            #     # receive는 사용자 입력 답변 # send는 채점 결과 또는 실패 알림
            #     fail, receive_message, send_message = self.process_user_ans_1(message_content) 
            #     if fail==False: # 처리 성공 
            #         self.now_stage ="quiz_2" # stage 상태 변경
            # elif self.now_stage == "quiz_2":
            #     fail, send_message = self.self.process_quiz_1()
            #     if fail==False: # 처리 성공
            #         self.now_stage ="user_ans_2" # stage 상태 변경
            # elif self.now_stage == "user_ans_2":
            #     fail, receive_message, send_message = self.process_user_ans_2(message_content)
            #     if fail==False: # 처리 성공 
            #         self.now_stage ="quiz_3" # stage 상태 변경
            # elif self.now_stage == "quiz_3":
            #     fail, send_message = self.self.process_quiz_1()
            #     if fail==False: # 처리 성공
            #         self.now_stage ="user_ans_3" # stage 상태 변경
            # elif self.now_stage == "user_ans_3":
            #     fail, receive_message, send_message = self.process_user_ans_3(message_content)
            #     if fail==False: # 처리 성공 
            #         self.now_stage ="feedback" # stage 상태 변경
            #         self.quizroom.cnt += 1

            # 모델 객체 변경 사항 저장
            self.quizroom.now_stage = self.now_stage
            self.quizroom.save()

            # 처리 성공 여부 파악 
            if fail: # 처리 실패
                self.send_json({"fail": send_message}) # 실패 메세지 전송
                if self.quizroom:  # 실패 메세지 객체 저장
                    QuizroomMessage.objects.create(
                        quizroom=self.quizroom,
                        message=send_message,
                        is_gpt=True
                    )
            else: # 처리 성공
                # 사용자 메세지 객체 생성 
                    # stage 변환된 상태라는 점 참고(["feedback", "user_ans_1",  "user_ans_2", "user_ans_3"]에서서 한 단계씩 밀린 상태)
                if self.now_stage in ["article", "quiz_2", "quiz_3", "feedback"]: # 사용자 (클라이언트 -> 서버)
                    QuizroomMessage.objects.create(
                        quizroom=self.quizroom,
                        message=receive_message,
                        is_gpt=False
                    )
                # gpt(시스템) 메세지 객체 생성 
                    # stage 변환된 상태라는 점 참고(마차낙지로 한 단계씩 밀린 상태)
                if self.now_stage in ["quiz_1", "user_ans_1", "quiz_2", "user_ans_2", "quiz_3", "user_ans_3", "feedback"]: # gpt (서버 -> 클라이언트) 
                    self.send_json({"message": send_message})
                    QuizroomMessage.objects.create(
                        quizroom=self.quizroom,
                        message=send_message,
                        is_gpt=True
                    )

                # 갱신된 stage 중 입력 메세지 필요없는 단계는 직접 호출
                if self.now_stage in ["article", "quiz_1", "quiz_2", "quiz_3"]: 
                    self.process_stage(None)

        else: # 퀴즈 종료
            self.finish_quiz()


    def process_feedback(self, message_content) -> Tuple[bool, str]: # 처리 실패 여부 반환
        print("사용자의 feedback 처리 중...")
            
        # 사용자 메세지 형식 검증
        if message_content=="":
            send_message = "입력값이 존재하지 않습니다. 다시 입력해주세요." 
            return True, send_message
                
        # 모델 수정&저장
        recieve_message = message_content
        self.quizroom.user_feedback_list.append(recieve_message)    # 기존 리스트에 새 요소 추가
        self.quizroom.save()    # Quizroom 모델 객체 변경 상태 DB 저장
        return False, recieve_message
    

    def process_article(self) -> Tuple[bool, str]: # 처리 실패 여부 반환
        print("article을 추천 중입니다.")
        # 초기화 
        send_message = "아티클 추천에 실패하였습니다." 
     
        # 키워드 추출 
        user_feedback = self.quizroom.user_feedback_list[self.quizroom.cnt]
        user_feedback_list = self.quizroom.user_feedback_list
        keyword_list = self.quizroom.keyword_list
                
        new_keywords, query = get_keywords_from_feedback(user_feedback, user_feedback_list, keyword_list)
        if new_keywords is None:
            send_message = "키워드 추출 에러가 발생하여 아티클 추천에 실패하였습니다. feedback을 다시 입력해주세요."
            del self.quizroom.user_feedback_list[self.quizroom.cnt]
            self.now_stage = "feedback"
            self.quizroom.now_stage = self.now_stage
            self.quizroom.save()
            return True, send_message
                    
        # 아티클 추천
        recommended_article = select_article(query, user_feedback_list) # 현재 사용자 요청 # 누적 사용자 요청 내역
        retry_extracted_keywords = recommended_article["retry_extracted_keywords"]

        # 아티클 본문 요약
        recommended_article['body'] = summarize_article(recommended_article['body'])

        # 아티클 생성 및 Room 연결
        article = Article.objects.create(
            quizroom=self.quizroom,
            user=self.user,
            user_feedback=user_feedback,
            title=recommended_article['title'],
            body=recommended_article['body'],
            url=recommended_article['url'],
            reason=recommended_article['reason'], # myquiz프로젝트에서
        )

        # 연결된 Room 객체 수정된 정보 저장
        if  retry_extracted_keywords is not None: # 키워드 추출이 재시도된 경우 
            if isinstance(retry_extracted_keywords, list):  # 리스트 형태인지 확인
                # 두 리스트 병합 # 중복 제거 # list 형태로 변환 
                self.quizroom.keyword_list = list(set(self.quizroom.keyword_list + retry_extracted_keywords))
        else:
            if isinstance(new_keywords, list):  # 리스트 형태인지 확인
                self.quizroom.keyword_list = list(set(self.quizroom.keyword_list + new_keywords))
                    
        self.quizroom.save() 

        # 메세지 형식 반환
        send_message = f"url: {article.url}\ntitle: {article.title} \nreason: {article.reason}" # 메세지 형식은 나중에 수정하기

        return False, send_message
    

    # # 1번_객관식 
    # def process_quiz_1(self) -> Tuple[bool, str]: # 처리 실패 여부 반환
    #     # 객관식 문제 생성 함수 호출(이전 구현 코드 2문제 동시에 생성하는 것 같은)
    #     # 문제 모델 객체로 (생성)저장
    #     # (퀴즈 1번 문제 가져오기)
    # def process_user_ans_1(self, message_content) -> Tuple[bool, str, str]: # 처리 실패 여부 반환
    #     # 사용자 답변 형식 검증 
    #     # 채점
    
    # # 2번_객관식 
    # def process_quiz_2(self) -> Tuple[bool, str]: # 처리 실패 여부 반환
    #     # (퀴즈 2번 문제 가져오기)
    # def process_user_ans_2(self, message_content) -> Tuple[bool, str, str]: # 처리 실패 여부 반환
    #     # 사용자 답변 형식 검증
    #     # 채점
         
    # # 3번_서술형 
    # def process_quiz_3(self) -> Tuple[bool, str]: # 처리 실패 여부 반환
    #   # 서술형 문제 생성 함수 호출
    # def process_user_ans_3(self, message_content) -> Tuple[bool, str, str]: # 처리 실패 여부 반환
    #   # 서술형 문제 답변 형식 검증 
    #   # 서술형 채점


    def finish_quiz(self): # 테스트용(코드 수정 필요)
        """퀴즈 종료 처리"""
        # 최종 점수 반환 & 종료 메세지
        print("🎉 수고하셨습니다. 퀴즈를 모두 마치셨습니다. 🎉") 




''' 
[사용자 인증]
# 1. 토큰 받아오기 
# 2. 토큰과 연결된 사용자 반환 
# 3. 해당 사용자에게 해당 id의 방 존재 여부 파악 
# 4. 방 반환
'''

'''
=> 사용자 입력 인식 (사용자 입력 기다려야 함)/ 입력 자동 인식후, procees_stage(message_content) 호출됨 
-> process 직접 수행 (바로 다음 단계 실행시켜야 함) / 우리가 직접 process_stage(None) 호출해야 함
[=> "feedback" -> "article" -> "quiz_1" => "user_ans_1" -> "quiz_2" => "user_ans_2" -> "quiz_3" => "user_ans_3" ]

[now_stage 흐름]
1. 사용자(feedback) > user_feedback 메세지 
2. gpt(article) > recommend Article 메세지 반환 

3. gpt(quiz_1) > 객관식 문제1 메세지 반환 
4. 사용자(user_ans_1) > 객관식 문제1 답 메세지 반환 
5. gpt(user_ans_1) > 채점 

6. gpt(quiz_2) > 객관식 문제2 메세지 반환 
7. 사용자(user_ans_2) > 객관식 문제2 답 메세지 반환 
8. gpt(user_ans_2) > 채점 

9.  gpt(quiz_3) > 서술형 문제 메세지 반환 
10. 사용자(user_ans_3) > 서술형 문제 답 메세지 반환 
11. gpt(user_ans_3) > 채점
'''