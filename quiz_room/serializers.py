# QuizRoom 생성 
# QuizRoom 

from rest_framework import serializers
from .models import Quizroom, QuizroomMessage, Article
from django.contrib.auth.models import User

# User 모델의 기본 Serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

# QuizroomMessage Serializer
class QuizroomMessageSerializer(serializers.ModelSerializer):
    quizroom = serializers.PrimaryKeyRelatedField(queryset=Quizroom.objects.all())  # Quizroom과 연결된 ID를 직렬화
    is_gpt = serializers.BooleanField()  # 메세지가 GPT에서 온 것인지 아닌지
    timestamp = serializers.DateTimeField()  # 메세지가 생성된 시간

    class Meta:
        model = QuizroomMessage
        fields = ['quizroom', 'message', 'is_gpt', 'timestamp']


# Article Serializer
class ArticleSerializer(serializers.ModelSerializer):
    quizroom = serializers.PrimaryKeyRelatedField(queryset=Quizroom.objects.all())  # Article과 연결된 Quizroom
    user = UserSerializer(read_only=True)  # 유저에 대한 정보는 UserSerializer로 직렬화
    user_feedback = serializers.CharField()  # 사용자 피드백
    title = serializers.CharField()  # 아티클의 제목
    url = serializers.URLField()  # 아티클의 URL
    body = serializers.CharField()  # 아티클 본문
    reason = serializers.CharField()  # 추천 이유

    class Meta:
        model = Article
        fields = ['quizroom', 'user', 'user_feedback', 'title', 'url', 'body', 'reason']


# Quizroom Serializer
class QuizroomSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # 유저 정보는 read_only로 직렬화
    keyword_list = serializers.ListField(child=serializers.CharField(), required=False)  # 키워드 리스트
    user_feedback_list = serializers.ListField(child=serializers.CharField(), required=False)  # 사용자 피드백 리스트
    start_date = serializers.DateTimeField()  # 시작 날짜
    end_date = serializers.DateTimeField(allow_null=True, required=False)  # 종료 날짜 (선택적)
    total_score = serializers.IntegerField()  # 총 점수
    cnt = serializers.IntegerField()  # 퀴즈 사이클 카운트

    # 관련된 메시지 및 아티클을 nested로 포함
    messages = QuizroomMessageSerializer(many=True, read_only=True)
    articles = ArticleSerializer(many=True, read_only=True)

    class Meta:
        model = Quizroom
        fields = ['user', 'keyword_list', 'user_feedback_list', 'start_date', 'end_date', 'total_score', 'cnt', 'messages', 'articles']
