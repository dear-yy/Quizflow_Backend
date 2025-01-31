from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save # 설정된 모델 객체 생성&저장 시 신호 생성
from django.dispatch import receiver # 신호 수신

# 1:1 방식으로 User 모델 (연결)확장
class Profile(models.Model):
    # User가 삭제될 때, 해당 프로필도 삭제
    # Profile의 기본 키를 User 모델의 pk로 설정(통합적으로 관리)
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    nickname = models.CharField(max_length=128)
    image = models.ImageField(upload_to='profile/', default='default.png') # 업로드 경로 & 기본 이미지 설정
    ranking_score = models.IntegerField(default=0)  # 랭킹 점수 추가

    def __str__(self):
        return self.nickname



# User 객체 생성 시, 연결될 새로운 Profile 객체 생성 함수
@receiver(post_save, sender=User) # User 모델의 객체에 대해 post_save 신호가 발생하면, receiver로 자동 감지
def create_user_profile(sender, instance, created, **kargs): # 다음 함수를 실행시킴
    # sender: 신호를 발생시킨 모델, 즉 User 모델이 전달됨 
    # instance: User 모델의 객체가 전달됨
    # created: 사용자(User 모델의 객체)가 새로 생성되었는지 여부를 나타내는 Boolean 값(create->True / save->False)
    # **kargs: 나머지 키워드 인자들을 받을 수 있는 부분

    if created: # 새 User 객체가 생성될 때만 프로필을 생성하도록
        # Profile 모델의 user 필드에 새로 생성된 User 객체(instance)를 할당 후, 새로운 Profile 객체 생성하여여 DB에 저장
        Profile.objects.create(user=instance) 
        