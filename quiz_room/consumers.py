# quiz_room.consumers.py 

# 웹소켓 클라이언트와 텍스트 데이터 송수신 시에 Json 직렬화&역직렬화까지 모두 처리 
from channels.generic.websocket import JsonWebsocketConsumer
# import openai
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from quiz_room.models import Quizroom, QuizroomMessage
# from django.views.decorators.csrf import csrf_exempt

''' 
# 1. 토큰 받아오기 
# 2. 토큰과 연결된 사용자 반환 
# 3. 해당 사용자에게 해당 id의 방 존재 여부 파악 
# 4. 방 반환
'''

'''
[now_stage 흐름]
1. 사용자(feedback) > user_feedback 메세지 
2. gpt(article) > recommend Article 메세지 반환 

3. gpt(quiz_1) > 객관식 문제1 메세지 반환 
4. 사용자(user_ans_1) > 객관식 문제1 답 메세지 반환 
5. gpt(grading_1) > 채점 

6. gpt(quiz_2) > 객관식 문제2 메세지 반환 
7. 사용자(user_ans_2) > 객관식 문제2 답 메세지 반환 
8. gpt(grading_2) > 채점 

9.  gpt(quiz_3) > 서술형 문제 메세지 반환 
10. 사용자(user_ans_3) > 서술형 문제 답 메세지 반환 
11. gpt(grading_3) > 채점
'''

# 서버측 웹소켓 연결 처리 
class QuizroomConsumer(JsonWebsocketConsumer):
    def connect(self):
        print("연결 중입니다.")
        self.user = None # 인증 전이므로, None으로 초기화
        self.room = None # 조회 전이므로, None으로 초기화
        self.now_stage = None  # 퀴즈 진행 상태 초기화
        self.accept()

    def disconnect(self, close_code):
        print("연결을 중단합니다.")
        self.user = None  # 사용자 정보 초기화
        self.room = None # 방 정보 초기화
        self.now_stage = None  # 퀴즈 진행 상태 초기화
        
    def receive_json(self, content_dict, **kwargs):
        if self.user is None: # 사용자 인증 전 상태
            # 1. 토큰 검사
            token = content_dict.get("token") # 클라이언트에서 보낸 토큰 가져오기
            if token: # 토큰 입력 존재
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
            self.room = self.get_room() # 채팅방 조회
            if self.room is None: 
                print("조회할 수 없는 방이므로 연결이 종료됩니다...")
                self.close() # 존재하지 않는 방이면 연결 거부
                return 
            else: 
                print(f"[{self.user}의 방]") # 해당 방으로 연결

            # 3. 퀴즈 진행 상태 검사, cnt 값 검증
            if self.room.cnt >= 3:
                print("완료된 퀴즈룸 입니다. 연결을 종료합니다.")
                self.send_json({"error": "최대 퀴즈 수를 초과했습니다." })
                self.close()
                return


        else:  # 이미 인증된 사용자인 경우
            print(f"📩 {self.user}의 메시지: {content_dict}")
            # 메시지 내용 모델 객체로 저장
            message_content = content_dict.get("message")
            if message_content:
                if self.room: 
                    QuizroomMessage.objects.create(
                        quizroom=self.room,
                        message=message_content,
                        is_gpt=False # 일단 사용자 메세지로 셋팅
                    )

        # 4. 퀴즈 진행 상태 복원
        # self.quiz_stage = self.room.quiz_stage # 아직 모델 수정 안해뒀음 
        # 예를 들어, cnt 값에 따라 퀴즈 단계를 설정할 수 있음
        # if self.now_stage is None:
            # self.now_stage = self.room.cnt  # 퀴즈 상태는 cnt 값에 기반
            # print(f"🔄 이전 퀴즈 상태 복원: {self.now_stage + 1}번 아티클 진행 중입니다.")

        # 현재 stage가 완료되면 다음 stage로 갱신하는 로직
        # 예시로, 퀴즈 (grading_3)단계가 끝날 때마다 cnt 값을 증가시킬 수 있음

        # else:  # 이미 인증된 사용자인 경우
            # print(f"📩 {self.user}의 메시지: {content_dict}")


        # print(f"🔄 이전 퀴즈 상태 복원: {self.room.cnt + 1}번 아티클 {self.quiz_stage}")
        # 현재 stage완료 시 다음 stage로 갱신하는 로직 구현하기

            
            # 5. 메시지 내용 모델 객체로 저장
            # message_content = content_dict.get("message")
            # if message_content:
                # if self.room: 
                    # QuizroomMessage.objects.create(
                        # quizroom=self.room,
                        # message=message_content,
                        # is_gpt=False # 일단 사용자 메세지로 셋팅
                    # )
                    # 6. cnt 값 증가 및 저장
                    # self.room.cnt += 1
                    # self.room.save()
                    # print(f"퀴즈 수 업데이트: 현재 cnt 값은 {self.room.cnt}입니다.")


    # 채팅방 조회
    def get_room(self) -> Quizroom | None: # 채팅방 존재하면 인스턴스 반환, 없으면 None 반환 
        room: Quizroom = None # 초기값을 None으로 설정하여, 방 못찾으면 그대로 반환 

        # 퀴즈룸 pk 
            # routing.py에서 url captured value로서 quizroom_id를 지정했었음
        quizroom_id = self.scope["url_route"]["kwargs"]["quizroom_id"]

        # 사용자 소유 방인지 
        print(f"사용자 {self.user}의 {quizroom_id}번 방 조회... ")    
        try:
            room = Quizroom.objects.get(pk=quizroom_id, user=self.user)
        except Quizroom.DoesNotExist: # 로그인 유저에 대해 채팅방을 못찾은 경우 
            print("현재 조회중인 방은 사용자의 방이 아닙니다.")
            pass
       
        # 조회한 채팅방 객체 반환
        return room 
   



# 추천 아티클 생성 로직 참고하기~
'''
room_id = kwargs.get("room_id") # 현재 url에서 <int:room_id> 인자 가져오기
        try: # 로그인한 유저의 특정 룸만 조회
            room = Room.objects.get(pk=room_id, user=request.user)
        except Room.DoesNotExist:
            return Response({"error": "방을 찾을 수 없거나 접근이 승인되지 않았습니다"}, status=status.HTTP_404_NOT_FOUND)

        
        serializer = ArticleCreateSerializer(data=request.data) # 역직렬화 
        if serializer.is_valid(): # 입력(역직렬화) 데이터 검증
            user_feedback = serializer.validated_data['user_feedback']
            
            # 키워드 추출 
            user_feedback_list = room.user_feedback_list
            keyword_list = room.keyword_list
    
            new_keywords, query = get_keywords_from_feedback(user_feedback, user_feedback_list, keyword_list)
            if new_keywords is None:
                return Response({"errors": "키워드 추출 에러가 발생하여 아티클 추천에 실패하였습니다. user_feedback을 다시 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST) 
                
            # 아티클 추천
            recommended_article = selectArticle(query, user_feedback_list) # 현재 사용자 요청 # 누적 사용자 요청 내역
            retry_extracted_keywords = recommended_article["retry_extracted_keywords"]
            # 아티클 생성 및 Room 연결
            article = Article.objects.create(
                user=request.user,
                room=room,
                user_feedback=user_feedback,
                title=recommended_article['title'],
                body=recommended_article['body'],
                url=recommended_article['url'],
                # reason=recommended_article['reason'], # myquiz프로젝트에서
            )

            # 연결된 Room 객체 수정된 정보 저장
            if  retry_extracted_keywords is not None: # 키워드 추출이 재시도된 경우 
                if isinstance(retry_extracted_keywords, list):  # 리스트 형태인지 확인
                    # 두 리스트 병합 # 중복 제거 # list 형태로 변환 
                    room.keyword_list = list(set(room.keyword_list + retry_extracted_keywords))
            else:
                if isinstance(new_keywords, list):  # 리스트 형태인지 확인
                    room.keyword_list = list(set(room.keyword_list + new_keywords))
            room.save() 

            # 새로 생성된 아티클 직렬화 후 반환
            article_serializer = ArticleSerializer(article)
            return Response(
                {"message": "아티클이 성공적으로 추천(생성)되었습니다!", "article": article_serializer.data},
                status=status.HTTP_201_CREATED
            )
        # 역직렬화 수행한 시리얼라이저 검증 실패 시(ex> 입력 형식 에러)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST) 


    
'''