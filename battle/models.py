from django.db import models
from django.contrib.auth.models import User

# Battleroom 모델
class Battleroom(models.Model):
    player_1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="player1_battleroom")
    player_2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="player2_battleroom")
    player_1_connected = models.BooleanField(default=False)
    player_2_connected = models.BooleanField(default=False)
    # stage [article -> quiz_1 -> quiz_1_ans -> quiz_2 -> quiz_2_ans -> quiz_3 -> quiz_3_ans -> finish -> end]
    now_stage_1 = models.CharField(max_length=50, default="article")  
    now_stage_2 = models.CharField(max_length=50, default="article")
    start_date= models.DateTimeField(null=True, blank=True) # 아티클&퀴즈 생성 완료시 활성화
    end_date_1 = models.DateTimeField(null=True, blank=True) 
    end_date_2 = models.DateTimeField(null=True, blank=True) 
    total_score_1 = models.IntegerField(default=0)
    total_score_2 = models.IntegerField(default=0)

    # 배틀룸 종료 여부 필드 추가(두 player 모두 end_date가 업데이트되면, True로)
    is_ended = models.BooleanField(default=False)  # 배틀룸이 종료되었는지 여부를 나타냄


class BattleArticle(models.Model):
    battleroom = models.ForeignKey(Battleroom, on_delete=models.CASCADE, related_name="article") 
    title =  models.TextField()
    url = models.URLField()
    body = models.TextField()


class BattleQuiz(models.Model):
    battleroom = models.OneToOneField(Battleroom, on_delete=models.CASCADE, related_name="battle_quiz")  # 1:1 관계
    battle_article = models.OneToOneField(BattleArticle, on_delete=models.CASCADE, related_name="battle_quiz")  # 1:1 관계
    quiz_1 = models.TextField()
    quiz_1_ans = models.IntegerField()
    quiz_2 = models.TextField(null=True, blank=True)
    quiz_2_ans = models.IntegerField(null=True, blank=True)
    quiz_3 = models.TextField(null=True, blank=True)
    quiz_3_ans = models.TextField(null=True, blank=True)