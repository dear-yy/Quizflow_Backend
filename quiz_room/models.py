from django.db import models
from django.contrib.auth.models import User

# Quizroom 모델: 한 명의 유저만 참여할 수 있는 방
class Quizroom(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rooms") # 유저가 생성한 quizroom 접근 (user.rooms.all)
    now_stage = models.CharField(max_length=50, default="feedback")  # 메세지 복원 시 활용할 필드
    keyword_list = models.JSONField(default=list, null=True, blank=True) # 아티클 생성에 활용
    user_feedback_list = models.JSONField(default=list, null=True, blank=True) # 아티클 생성에 활용
    start_date = models.DateTimeField(auto_now_add=True) # 처음 생성될 때만 
    update_date = models.DateTimeField(auto_now=True) # 갱신된 시간 (생성&수정)
    end_date = models.DateTimeField(null=True, blank=True) # cnt가 3이 될 경우 등록
    total_score = models.IntegerField(default=0)
    cnt = models.IntegerField(default=0) # 1개의 아티클에 대한 퀴즈 사이클 완료 시 # quiz3 사용자가 답변을 제출한 순간 카운트 됨 # 아티클 조회 시 사용해도 될 듯 


# QuizroomMessage 모델: Quizroom 모델에서 생성되는 모든(user&gpt) 메세지 기록
class QuizroomMessage(models.Model):
    quizroom = models.ForeignKey(Quizroom, on_delete=models.CASCADE, related_name="messages") # quizroom에 속한 메세지 접근(quizroom.messages.all)
    message = models.TextField(null=True, blank=True)
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
    timestamp = models.DateTimeField(auto_now_add=True)  # 생성될 때 자동으로 시간 저장


class MultipleChoiceQuiz(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE, related_name="multiple_choice_quiz")  # 1:1 관계
    quiz_1 = models.TextField()
    quiz_1_ans = models.IntegerField()
    quiz_2 = models.TextField(null=True, blank=True)
    quiz_2_ans = models.IntegerField(null=True, blank=True)

class DescriptiveQuiz(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE, related_name="descriptive_quiz")  # 1:1 관계
    quiz_3 = models.TextField()
    quiz_3_ans = models.TextField()


# 아티클 중복 방지를 위한 모델 
class UserArticleHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="article_history")
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="viewed_by")
    timestamp = models.DateTimeField(auto_now_add=True)  # 저장된 시간

    class Meta:
        ordering = ["-timestamp"]  # 최신순 정렬