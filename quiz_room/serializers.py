from rest_framework import serializers
from .models import Quizroom, QuizroomMessage, Article
from users.serializers import UserSerializer

# QuizroomMessage Serializer
class QuizroomMessageSerializer(serializers.ModelSerializer):
    quizroom = serializers.PrimaryKeyRelatedField(queryset=Quizroom.objects.all())  # QuizroomMessageSerializer과 연결된 Quizroom의 ID를 직렬화 # 특정 방의 메세지 정보 불러올때 활용 

    class Meta:
        model = QuizroomMessage
        fields = ['quizroom', 'message', 'is_gpt', 'timestamp']


# Article Serializer
class ArticleSerializer(serializers.ModelSerializer):
    quizroom = serializers.PrimaryKeyRelatedField(queryset=Quizroom.objects.all())  # Article과 연결된 Quizroom의 id 직렬화 # 특정 방의 아티클 정보 불러올때 활용 

    # 유저 nested로 포함
    user = UserSerializer(read_only=True)  # 유저에 대한 정보는 UserSerializer로 직렬화 # 필요 없을 수도?!

    class Meta:
        model = Article
        fields = ['quizroom', 'user', 'user_feedback', 'title', 'url', 'body', 'reason']

# Article Create Serializer
class ArticleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['user_feedback']


# Quizroom Serializer
class QuizroomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quizroom
        fields = ['id']

# Quizroom List Serializer
class QuizroomListSerializer(serializers.ModelSerializer):
    end_date = serializers.DateTimeField(allow_null=True, required=False)  # 종료 날짜 (선택적)
    
    class Meta:
        model = Quizroom
        fields = ['id','start_date', 'update_date', 'end_date', 'total_score', 'cnt']


# Message List Serializer
class MessageListSerializer(serializers.ModelSerializer):

    # 관련된 유저,메시지 및 아티클을 nested로 포함 # read_only로 직렬화
    user = UserSerializer(read_only=True) 
    messages = QuizroomMessageSerializer(many=True, read_only=True)
    articles = ArticleSerializer(many=True, read_only=True)

    class Meta:
        model = Quizroom
        fields = ['id', 'user', 'start_date', 'total_score', 'cnt', 'messages', 'articles']
