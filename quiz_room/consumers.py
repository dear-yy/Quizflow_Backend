# quiz_room.consumers.py 

# 웹소켓 클라이언트와 텍스트 데이터 송수신 시에 Json 직렬화&역직렬화까지 모두 처리 
from channels.generic.websocket import JsonWebsocketConsumer
# import openai
from typing import Tuple
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.utils.timezone import now
from django.contrib.auth.models import User
from quiz_room.models import Quizroom, QuizroomMessage, Article, MultipleChoiceQuiz,  DescriptiveQuiz, UserArticleHistory
from functions.quizroom.selectArticle import get_keywords_from_feedback, select_article                  # 아티클 추천 기능
from functions.quizroom.summarization import summarize_article                                           # 요약 기능 
from functions.quizroom.multipleChoiceQuiz import generate_multiple_choice_quiz_with_check, check_answer # 객관식 퀴즈
from functions.quizroom.descriptiveQuiz import generate_descriptive_quiz, evaluate_descriptive_answer  # 서술형 퀴즈
import json


# 서버측 웹소켓 연결 처리 
class QuizroomConsumer(JsonWebsocketConsumer):
    def connect(self):
        print("ℹ️ 연결 중입니다.")
        self.user = None # 사용자 인증 전 초기화
        self.quizroom = None # 조회 전 초기화
        self.now_stage = None  # 퀴즈 진행 상태 초기화
        self.article = None # 현재 진행중인 아티클 
        self.accept()

    def disconnect(self, close_code):
        print("ℹ️ 연결을 중단합니다.")
        self.user = None
        self.quizroom = None
        self.now_stage = None
        self.article = None 

    def receive_json(self, content_dict, **kwargs):
        type = content_dict.get("type")
        if self.user is None and type=="auth": # 사용자 인증 전
            # 1. 토큰 검사
            token = content_dict.get("token") # 클라이언트 소유 토큰
            if token :
                try: 
                    self.user = Token.objects.get(key=token).user # 토큰 소유 사용자 객체
                except Token.DoesNotExist: # 유효하지 않은 토큰
                    self.close_on_failure('❌ 유효하지 않은 토큰입니다.')
                    return 
            else: 
                self.close_on_failure("❌ 토큰이 존재하지 않습니다.")
                return 

            # 2. 채팅방 조회
            self.quizroom = self.get_quizroom() # 채팅방 조회
            if self.quizroom is None: 
                self.close_on_failure("❌ 존재하지 않는 퀴즈룸입니다.")
                return 
            print("ℹ️ 웹소켓 연결 완료") 
            
            # 3. 일일 제한 검사 
            today = timezone.now().date()  
            quiz_update_cnt = Quizroom.objects.filter(user=self.user, update_date__date=today).count() # '오늘' 수정된 퀴즈룸 개수
            if quiz_update_cnt>=3 and self.quizroom.update_date.date()!=today:
                self.close_on_failure(f"❌ 일일 제한 초과: {quiz_update_cnt}")
                self.send_json({"error": "일일 제한 초과"})
                return
            
            # 4. 퀴즈 종료 여부
            if self.quizroom.cnt > 3:
                self.close_on_failure("❌ 이미 완료된 퀴즈룸 입니다.")
                return
            elif self.quizroom.cnt == 3:
                self.finish_quiz()
        
            # 5. 퀴즈 진행 상태&아티클 복원
            self.now_stage = self.quizroom.now_stage
            self.article = self.quizroom.articles.order_by("-timestamp").first() # 현재 quizroom에서 최근에 추가된 아티클 반환
            latest_message = QuizroomMessage.objects.filter(quizroom=self.quizroom).order_by('-timestamp').first() # 최근 메세지 존재 여부파악 (-> 피드백 요청 메세지 중복 전송 방지)
            print(f'🔔 {self.now_stage}부터 시작합니다.') 

            # 6. 퀴즈 진행(gpt 답변 단계에서 중단된 경우)
            if self.now_stage in ["article", "quiz_1", "quiz_2", "quiz_3"]:
                self.process_stage(None)

            # 7. 퀴즈룸 최초 실행인 경우
            if self.now_stage in ["feedback"] and self.quizroom.cnt == 0:
                send_message =  f"{self.user.profile.nickname}님 안녕하세요!\n🔍 어떤 주제에 대해 학습하고 싶으신가요? 입력해주시면 관련된 퀴즈로 안내드릴게요!\n" # 사용자 프로필 명으로 변경하기~!
                if latest_message==None: # 최초 피드백 요청 메세지 중복 전송 방지
                    self.gpt_send_message(send_message)
                    
        elif type=="user":  # 인증된 사용자
            # 퀴즈 진행 단계에 따른 사용자 입력 처리
            message_content = content_dict.get("message")
            self.process_stage(message_content)


    # 채팅방 조회
    def get_quizroom(self) -> Quizroom | None:
        quizroom: Quizroom = None # 못 찾으면 그대로 반환 
        quizroom_id = self.scope["url_route"]["kwargs"]["quizroom_id"] # quizroom_id값 -> routing.py의 url에서 가져옴

        try: # 사용자 소유 여부 파악 
            print(f"🔄 사용자 {self.user}의 {quizroom_id}번 방 조회... ")    
            quizroom = Quizroom.objects.get(pk=quizroom_id, user=self.user)
        except Quizroom.DoesNotExist: # 로그인 유저에 대해 채팅방을 못찾은 경우 
            pass
        return quizroom 


    def process_stage(self, message_content):
        fail = True             # 처리 성공하면 False
        receive_message = None  # 사용자(클라이언트 -> 서버) / 답변, 피드백 메세지지
        send_message = None     # gpt(서버 -> 클라이언트) / 퀴즈 메세지, 실패 알림
        
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
                fail, send_message = self.process_quiz_1()
                if fail==False: # 처리 성공
                    self.now_stage ="user_ans_1" # stage 상태 변경
            elif self.now_stage == "user_ans_1":
                fail, receive_message, send_message = self.process_user_ans_1(message_content) 
                if fail==False: # 처리 성공 
                    self.now_stage ="quiz_2" # stage 상태 변경

            elif self.now_stage == "quiz_2":
                fail, send_message = self.process_quiz_2()
                if fail==False: # 처리 성공
                    self.now_stage ="user_ans_2" # stage 상태 변경
            elif self.now_stage == "user_ans_2":
                fail, receive_message, send_message = self.process_user_ans_2(message_content)
                if fail==False: # 처리 성공 
                    self.now_stage ="quiz_3" # stage 상태 변경

            elif self.now_stage == "quiz_3":
                fail, send_message = self.process_quiz_3()
                if fail==False: # 처리 성공
                    self.now_stage ="user_ans_3" # stage 상태 변경
            elif self.now_stage == "user_ans_3":
                fail, receive_message, send_message = self.process_user_ans_3(message_content)
                if fail==False: # 처리 성공 
                    self.now_stage ="feedback" # stage 상태 변경
                    self.quizroom.cnt += 1
                    self.article = None # 새 아티클 갱신 준비

            # 모델 객체 변경 사항 저장
            self.quizroom.now_stage = self.now_stage
            self.quizroom.save()

            # 처리 성공 여부 파악 
            if fail: # 실패
                if self.now_stage in ["user_ans_1", "user_ans_2", "user_ans_3"]: # 사용자 입력력 메세지
                    self.user_send_message(receive_message) # 실패 처리된 사용자 메세지도 저장
                self.gpt_send_message(send_message) # 에러(gpt) 메세지 저장
            else: # 성공
                # 성공 처리를 통해 다음 상태로 stage '다음 상태'로 갱신된 점 고려하기!
                
                if self.now_stage in ["article", "quiz_2", "quiz_3", "feedback"]: 
                    self.user_send_message(receive_message) # 사용자 (클라이언트 -> 서버)

                if self.now_stage in ["quiz_1", "user_ans_1", "quiz_2", "user_ans_2", "quiz_3", "user_ans_3", "feedback"]: 
                    self.gpt_send_message(send_message) # gpt (서버 -> 클라이언트) 

                    # 사용자 피드백 입력 요청 메세지 
                    if self.now_stage in ["feedback"] and self.quizroom.cnt < 3: # 퀴즈 진행 중
                        send_message = "🔍 해당 아티클을 읽고 더 궁금한거나, 이해하기 어려운 부분에 대해 입력해주세요.\n(입력 내용은 다음 아티클 출제에 반영됩니다.)\n"
                        self.gpt_send_message(send_message)
                    elif self.now_stage in ["feedback"] and self.quizroom.cnt == 3: # 퀴즈 종료(<- 퀴즈 진행 중 도달)
                        self.finish_quiz()

                # 갱신된 stage 중 사용자 입력 필요없는 단계는 직접 호출
                if self.now_stage in ["article", "quiz_1", "quiz_2", "quiz_3"]: 
                    self.process_stage(None)


    def process_feedback(self, message_content) -> Tuple[bool, str]: # 처리 실패 여부 반환
        # 사용자 메세지 형식 검증
        if message_content=="":
            send_message = "입력값이 존재하지 않습니다. 다시 입력해주세요." 
            return True, send_message
                
        # 모델 수정&저장
        self.quizroom.user_feedback_list.append(message_content)    # 기존 리스트에 새 요소 추가
        self.quizroom.save()    # Quizroom 모델 객체 변경 상태 DB 저장
        return False, message_content
    

    def process_article(self) -> Tuple[bool, str]: # 처리 실패 여부 반환
        send_message = "아티클을 조회중입니다. 잠시만 기다려주시면, 아티클을 추천해 드릴게요!"
        self.gpt_send_message(send_message)
        
        # 초기화 
        send_message = "아티클 추천에 실패하였습니다." 
        recent_user_feedback = self.quizroom.user_feedback_list[self.quizroom.cnt] 
        user_feedback_list = self.quizroom.user_feedback_list
        keyword_list = self.quizroom.keyword_list 
        
        # 키워드 추출
        new_keywords, search_query = get_keywords_from_feedback(recent_user_feedback, user_feedback_list, keyword_list)
        print(f"🔍 추출 키워드 {new_keywords}")

        if new_keywords == []:
            send_message = "키워드 추출 에러가 발생하여 아티클 추천에 실패하였습니다. feedback을 다시 입력해주세요."
            del self.quizroom.user_feedback_list[self.quizroom.cnt]
            self.now_stage = "feedback"
            self.quizroom.now_stage = self.now_stage
            self.quizroom.save()
            return True, send_message
                    
        # 아티클 추천
        recommended_article = select_article(self.user, search_query, user_feedback_list) # 현재 사용자 요청 # 누적 사용자 요청 내역
        retry_extracted_keywords = recommended_article["retry_extracted_keywords"]
        print(f"🔍 재추출 키워드 {retry_extracted_keywords}")

        # 아티클 본문 요약
        recommended_article['body'] = summarize_article(recommended_article['body'])

        # 아티클 생성 및 Room 연결
        self.article = Article.objects.create(
            quizroom=self.quizroom,
            user=self.user,
            user_feedback=recent_user_feedback,
            title=recommended_article['title'],
            body=recommended_article['body'],
            url=recommended_article['url'],
            reason=recommended_article['reason'],
        )


        # 아티클 중복 방지를 위한 사용자 아티클 정보 저장
        UserArticleHistory.objects.create(user=self.user, article=self.article)

        # 최근 100개만 유지 (초과 시 가장 오래된 기록 삭제)
        history_count = UserArticleHistory.objects.filter(user=self.user).count()
        if history_count > 100: 
            oldest_entry = UserArticleHistory.objects.filter(user=self.user).order_by("timestamp").first()
            if oldest_entry:
                oldest_entry.delete()

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
            # title에 따옴표 있는 경우 존재 -> json 파싱을 위한 처리 추가하기!!!
        send_message_dic = {"url":self.article.url, "title":self.article.title, "reason":self.article.reason}
        
        # JSON 문자열 변환 및 따옴표 이스케이프 처리
        send_message = json.dumps(send_message_dic, ensure_ascii=False) # 대체 코드 # send_message = f"{send_message_dic}" 
        return False, send_message
    

    # 1번_객관식 
    def process_quiz_1(self) -> Tuple[bool, str]: # 처리 실패 여부 반환
        quiz_1, ans_1 = generate_multiple_choice_quiz_with_check(self.article.body, previous_quiz=None)
        quiz = MultipleChoiceQuiz.objects.create(
            article=self.article,
            quiz_1=quiz_1,
            quiz_1_ans=ans_1,
            quiz_2=None,  # quiz_2를 비워두고
            quiz_2_ans=None  # quiz_2_ans를 비워둘 수 있음
        )
        if quiz.id: # 정상 생성됨
            quiz.save()
            return (False, f"1️.\n{quiz_1}\n ** 번호만 입력해주세요")
        else:
            return (True, "1번 객관식 퀴즈 생성을 실패하였습니다.")
        
    def process_user_ans_1(self, message_content) -> Tuple[bool, str, str]: # 처리 실패 여부 반환
        quiz_1_ans = self.article.multiple_choice_quiz.quiz_1_ans
        fail, send_message, score = check_answer(message_content, quiz_1_ans) 
        # 점수 반영 로직 추가
        if fail: # 채점 실패(사용자 입력 형식 문제)
            return True, message_content, send_message
        else: # 채점 성공
            self.quizroom.total_score += score # quizroom에 점수 반영
            return False, message_content, send_message 
    
    # 2번_객관식 
    def process_quiz_2(self) -> Tuple[bool, str]: # 처리 실패 여부 반환
        multiple_choice_quiz = self.article.multiple_choice_quiz # 이전에 생성해둔 객관식 퀴즈 객체 반환
        if multiple_choice_quiz.id: # 객관식 퀴즈 존재하면
            quiz_1 = multiple_choice_quiz.quiz_1
            quiz_2, ans_2 = generate_multiple_choice_quiz_with_check(self.article.body, previous_quiz=quiz_1)
            multiple_choice_quiz.quiz_2 = quiz_2
            multiple_choice_quiz.quiz_2_ans = ans_2
            multiple_choice_quiz.save()
            return (False, f"2️.\n{quiz_2}\n ** 번호만 입력해주세요")
        else:
            return (True, "2번 객관식 퀴즈 생성을 실패하였습니다.")
        
    def process_user_ans_2(self, message_content) -> Tuple[bool, str, str]: # 처리 실패 여부 반환
        quiz_2_ans = self.article.multiple_choice_quiz.quiz_2_ans
        fail, send_message, score = check_answer(message_content, quiz_2_ans) 
        # 점수 반영 로직 추가
        if fail: # 채점 실패(사용자 입력 형식 문제)
            return True, message_content, send_message
        else: # 채점 성공
            self.quizroom.total_score += score # quizroom에 점수 반영
            return False, message_content, send_message
         
    # 3번_서술형 
    def process_quiz_3(self) -> Tuple[bool, str]: # 처리 실패 여부 반환
        quiz_3, ans_3 = generate_descriptive_quiz(self.article.body)
        quiz = DescriptiveQuiz.objects.create(
            article=self.article,
            quiz_3=quiz_3,
            quiz_3_ans=ans_3
        )
        if quiz.id: # 정상 생성됨
            quiz.save()
            return (False, f"3️.\n{quiz_3}\n ** 2문장 이내로 답변을 입력해주세요")
        else:
            return (True, "3번 서술형 퀴즈 생성을 실패하였습니다.")
        
    def process_user_ans_3(self, message_content) -> Tuple[bool, str, str]: # 처리 실패 여부 반환
        descriptive_quiz = self.article.descriptive_quiz
        fail, feedback, score = evaluate_descriptive_answer(message_content, descriptive_quiz.quiz_3, descriptive_quiz.quiz_3_ans) 
        # 점수 반영 로직 추가
        if fail: # 채점 실패(json 변환 오류 문제)
            send_message = "채점 과정에서 에러가 발생하였습니다."
            return True, message_content, send_message
        else: # 채점 성공
            send_message = feedback
            self.quizroom.total_score += score # quizroom에 점수 반영
            return False, message_content, send_message


    def finish_quiz(self): # 퀴즈룸 종료 처리
        if self.quizroom.cnt == 3:
            # 프로필의 랭킹 점수 반영
            self.user.profile.ranking_score += self.quizroom.total_score
            self.user.profile.save()

            # 총점 메시지 
            send_message = f" 최종 점수: {self.quizroom.total_score}/30"
            self.gpt_send_message(send_message)
            # 종료 메세지
            send_message = " 수고하셨습니다. 퀴즈를 모두 마치셨습니다. "
            self.gpt_send_message(send_message)
            
            self.quizroom.cnt += 1
            self.quizroom.end_date = now()
            self.quizroom.save()  # 변경 사항을 DB에 저장
            self.close() # 웹소켓 연결 종료


    def user_send_message(self, receive_message):
        QuizroomMessage.objects.create(
            quizroom=self.quizroom,
            message=receive_message,
            is_gpt=False
        )

    def gpt_send_message(self, send_message):
        QuizroomMessage.objects.create(
            quizroom=self.quizroom,
            message=send_message,
            is_gpt=True
        )
        self.send_json({"message": send_message, "is_gpt": True})

    def close_on_failure(self, fail_message):
        print(fail_message)
        self.close()


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