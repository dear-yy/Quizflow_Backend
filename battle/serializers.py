from rest_framework import serializers
from .models import Battleroom
from users.serializers import ProfileSerializer  

# Quizroom List Serializer
class BattleroomListSerializer(serializers.ModelSerializer):
    # player_1과 player_2를 ProfileSerializer를 사용하여 직렬화
    player_1 = ProfileSerializer(source="player_1.profile", read_only=True) # player_1(User 객체)에서 Profile 모델
    player_2 = ProfileSerializer(source="player_2.profile", read_only=True) # player_2(User 객체)에서 Profile 모델

    class Meta:
        model = Battleroom
        fields = [
            'id', # battleroom의 id
            'player_1',
            'player_2',
            'total_score_1',
            'total_score_2',
            'start_date',
            'end_date_1',
            'end_date_2',
            'is_ended'  # 종료 여부
        ]


class NewBattleroomSerializer(serializers.ModelSerializer):
    # player_1과 player_2를 ProfileSerializer를 사용하여 직렬화
    player_1 = ProfileSerializer(source="player_1.profile", read_only=True) # player_1(User 객체)에서 Profile 모델
    player_2 = ProfileSerializer(source="player_2.profile", read_only=True) # player_2(User 객체)에서 Profile 모델
    
    class Meta:
        model = Battleroom
        fields = [
            'id', # battleroom의 id
            'player_1',
            'player_2'
        ]