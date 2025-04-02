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
    monthly_percentage = serializers.SerializerMethodField() 
    ranking_info = serializers.SerializerMethodField() 

    class Meta:
        model = User
        fields = ['profile', 'today_score', 'monthly_percentage', 'ranking_info']
    
    def get_today_score(self, obj):
        """ 사용자의 오늘 ranking_score 조회 """
        today = datetime.today().date()

        # 오늘의 배틀 점수 조회 
        battle_1_score = Battleroom.objects.filter(player_1=obj, end_date_1__date=today).aggregate(Sum('total_score_1'))['total_score_1__sum'] or 0
        battle_2_score = Battleroom.objects.filter(player_2=obj, end_date_2__date=today).aggregate(Sum('total_score_2'))['total_score_2__sum'] or 0

        # 오늘의 퀴즈 점수 조회(종료 건만 반영) 
        quiz_score = Quizroom.objects.filter(user=obj, end_date__date=today).aggregate(Sum('total_score'))['total_score__sum'] or 0

        return battle_1_score + battle_2_score + quiz_score
        
        
    def get_monthly_percentage(self, obj):
        """ 사용자가 이번 달 상위 몇 퍼센트인지 계산 (superuser 제외) """

        user_score = obj.profile.ranking_score or 0 
        all_scores = Profile.objects.filter(user__is_superuser=False).values_list("ranking_score", flat=True) # superuser 제외 모든 user

        # 점수를 내림차순 정렬
        sorted_scores = sorted(all_scores, reverse=True)  
        
        if not sorted_scores or user_score == 0: # 데이터가 없거나 점수가 0이면 
            return 100  

        rank = sorted_scores.index(user_score) + 1  # 내 순위 (index 특성상 +1)
        total_users = len(sorted_scores)  # superuser 제외한 전체 사용자 수

        return (rank / total_users) * 100  # 상위 몇 %인지 계산
    

    
    def get_ranking_info(self, obj):
        """ 상위 10순위까지 사용자 프로필 정보 (동점자 동일 순위 처리) """

        # superuser 제외 ranking_score 내림차순 정렬
        top_users = Profile.objects.filter(user__is_superuser=False).order_by('-ranking_score')

        ranking_info = []
        previous_score = None
        rank = 0 # 실제 순위(1~ ) # 동점은 유지 
        display_rank = 0  # 인덱스 순서(0~ ) # 동점 무관 카운트(==인원수)

        for user in top_users:
            if user.ranking_score != previous_score:  
                rank = display_rank + 1  # 새로운 점수면 새로운 순위 부여
            display_rank += 1  

            if rank > 10:  
                break  # 10순위까지만 출력

            serialized_user = ProfileInfoForRankingSerializer(user).data
            serialized_user["rank"] = rank  
            ranking_info.append(serialized_user)

            previous_score = user.ranking_score  # 갱신

        return ranking_info
