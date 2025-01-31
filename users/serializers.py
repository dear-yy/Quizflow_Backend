from django.contrib.auth.password_validation import validate_password # 패스워드  검증 도구
from django.contrib.auth import authenticate # 유저 인증(로그인) # settings.py에 REST_FRAMEWORK 항목에 token방식으로 설정해둠
from django.contrib.auth.models import User
from .models import Profile 
from rest_framework import serializers
from rest_framework.authtoken.models import Token # Token 모델 
from rest_framework.validators import UniqueValidator # 이메일 중복 방지용 검증 도구


# 회원가입용
class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required = True, # 필수 입력 항목
        validators = [UniqueValidator(queryset=User.objects.all())], # 이메일 중복 검증 
    )
    password = serializers.CharField(
        write_only = True, # 역직렬화만 허용(입력O 조회X)
        required = True, # 필수 입력 항목
        validators = [validate_password] # 비밀번호 검증 
    )
    password2 = serializers.CharField(
        write_only = True, # 역직렬화만 허용(입력O 조회X)
        required = True, # 필수 입력 항목
    )

    class Meta():
        model = User
        fields = ['username', 'password', 'password2', 'email']

    def validate(self, data): # 비밀번호 일치 여부 확인
        # 유효성 검증
        if data['password'] != data['password2']: #실패 # pw와 pw2 불일치 경우 
            raise serializers.ValidationError( {"password": "password와 password2가 일치하지 않습니다."})
        return data # 성공 
    
    def create(self, validated_data): # 유저&토큰 생성 
        # validated_data: 검증을 통과한 데이터를 포함하는 딕셔너리
        # 유저 생성
        user = User.objects.create_user(
            username=validated_data['username'], # username 설정
            email = validated_data['email'],  # email 설정
        )
        user.set_password(validated_data['password']) # 비밀번호 해시화
        user.save()
        # 토큰 생성
        token = Token.objects.create(user=user) # 해당 유저에 대한 인증 토큰 생성
        return user


# 로그인용 
class LoginSerializer(serializers.Serializer): # 모델과 상관없는 기능
    # 사용자에게 입력 요청할 필드
    username = serializers.CharField(required=True) # 필수 입력 항목 
    password = serializers.CharField(required=True, write_only=True) # 필수 입력 항목 # 역직렬화만 허용(입력O 조회X)

    # 로그인 인증 과정을 처리
    def validate(self, data): 
        # data는 클라이언트로 부터 시리얼라이저를 통해 입력받은 데이터를 포함하는 딕셔너리

        # 사용자 인증을 처리
            # data를 통해 username과 password를 검증하여, 일치하는 사용자를 반환
            # 인증이 성공하면 User 객체를 반환하고, 실패하면 None을 반환
        user = authenticate(**data)   

        if user: # 인증 성공 경우
            token = Token.objects.get(user=user) # 인증된 사용자에 대해서 user와 연결된 토큰을 찾아서 반환
            return token, user.id # 인증된 사용자와 연결된 토큰 & user의 pk 반환
        raise serializers.ValidationError({"error" : "아이디 또는 비밀번호가 올바르지 않습니다."}) # 인증 실패 경우
    


# 프로필용(수정, 조회)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "id"]  # User의 username과 email만 포함


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # UserSerializer를 read_only로 포함

    class Meta:
        model = Profile
        fields = ["user", "nickname", "image", "ranking_score"]  # ranking_score 필드 추가