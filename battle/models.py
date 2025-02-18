from django.db import models
from django.contrib.auth.models import User

# Battleroom 모델
class Battleroom(models.Model):
    player_1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="player1")
    player_2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="player2")
    now_stage_1 = models.CharField(max_length=50, default="feedback")  # 메세지 복원 시 활용할 필드
    now_stage_2 = models.CharField(max_length=50, default="feedback")
    start_date= models.DateTimeField(auto_now_add=True) # 처음 생성될 때만
    end_date_1 = models.DateTimeField(null=True, blank=True) 
    end_date_2 = models.DateTimeField(null=True, blank=True) 
    total_score_1 = models.IntegerField(default=0)
    total_score_2 = models.IntegerField(default=0)

    # 배틀룸 종료 여부 필드 추가(두 player 모두 end_date가 업데이트되면, True로)
    is_ended = models.BooleanField(default=False)  # 배틀룸이 종료되었는지 여부를 나타냄


class BattleArticle(models.Model):
    battleroom = models.ForeignKey(Battleroom, on_delete=models.CASCADE, related_name="articles") 
    title =  models.TextField()
    url = models.URLField()
    body = models.TextField()


class BattleQuiz(models.Model):
    # 퀴즈 조회시 배틀룸으로 조회하는 게 더 좋지 않을까? 배틀룸도 넣는게 좋을까?(고민)
    battle_article = models.OneToOneField(BattleArticle, on_delete=models.CASCADE, related_name="multiple_choice_quiz")  # 1:1 관계
    quiz_1 = models.TextField()
    quiz_1_ans = models.IntegerField()
    quiz_2 = models.TextField(null=True, blank=True)
    quiz_2_ans = models.IntegerField(null=True, blank=True)
    quiz_3 = models.TextField(null=True, blank=True)
    quiz_3_ans = models.TextField(null=True, blank=True)