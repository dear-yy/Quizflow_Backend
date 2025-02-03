from django.db import models
from django.contrib.auth.models import User

# Quizroom 모델: 한 명의 유저만 참여할 수 있는 방
class Quizroom(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rooms") # 유저가 생성한 quizroom 접근 (user.rooms.all)
    keyword_list = models.JSONField(default=list) # 아티클 생성에 활용
    user_feedback_list = models.JSONField(default=list) # 아티클 생성에 활용
    start_date = models.DateTimeField(auto_now_add=True) # 처음 생성될 때만 
    end_date = models.DateTimeField(null=True, blank=True) # cnt가 3이 될 경우 등록
    total_score = models.IntegerField(default=0)
    cnt = models.IntegerField(default=0) # 1개의 아티클에 대한 퀴즈 사이클 완료 시 # quiz3 사용자가 답변을 제출한 순간 카운트 됨


# QuizroomMessage 모델: Quizroom 모델에서 생성되는 모든(user&gpt) 메세지 기록
class QuizroomMessage(models.Model):
    quizroom = models.ForeignKey(Quizroom, on_delete=models.CASCADE, related_name="messages") # quizroom에 속한 메세지 접근(quizroom.messages.all)
    # user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_message") # 필요 없을 것 같기도?
    message = models.TextField()
    is_gpt = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True) # 처음 생성될 때만 

class Article(models.Model):
    quizroom = models.ForeignKey(Quizroom, on_delete=models.CASCADE, related_name="articles") # quizroom에 속한 아티클들 접근(quizroom.articles.all)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="articles") # user가 작성한 아티클들 접근 (user.articles.all)
    user_feedback = models.TextField()# 추천할 아티클의 주제에 대한 사용자 요청 
    title =  models.TextField()
    url = models.URLField()
    body = models.TextField()
    reason = models.TextField()