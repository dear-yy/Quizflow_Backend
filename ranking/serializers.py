from rest_framework import serializers
from django.db.models import Sum
from datetime import datetime
from django.contrib.auth.models import User
from users.models import Profile
from battle.models import Battleroom
from quiz_room.models import Quizroom
from users.serializers import ProfileInfoForRankingSerializer

class RankingBoardSerializer(serializers.ModelSerializer):
    profile = ProfileInfoForRankingSerializer(read_only=True)  # ProfileSerializer를 read-only로 포함
    
    # SerializerMethodField     # get_메소드명 -> 메소드명의 필드값으로 
    today_score = serializers.SerializerMethodField() 

    class Meta:
        model = User
        fields = ['profile', 'today_score']
    
    def get_today_score(self, obj):
        """ 사용자의 오늘 ranking_score 조회 """
        today = datetime.today().date()

        # 오늘의 배틀 점수 조회 
        battle_1_score = Battleroom.objects.filter(player_1=obj, end_date_1__date=today).aggregate(Sum('total_score_1'))['total_score_1__sum'] or 0
        battle_2_score = Battleroom.objects.filter(player_2=obj, end_date_2__date=today).aggregate(Sum('total_score_2'))['total_score_2__sum'] or 0

        # 오늘의 퀴즈 점수 조회 
        quiz_score = Quizroom.objects.filter(user=obj, update_date__date=today).aggregate(Sum('total_score'))['total_score__sum'] or 0

        return battle_1_score + battle_2_score + quiz_score

    # def get_monthly_percentage(self, obj):
