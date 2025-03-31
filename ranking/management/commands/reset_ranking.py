from django.core.management.base import BaseCommand
from users.models import Profile 

class Command(BaseCommand):
    help = "매달 1일 00:00에 모든 사용자의 ranking_score를 초기화합니다." # 해당 명령어 설명 메세지

    def handle(self, *args, **kwargs):
        Profile.objects.update(ranking_score=0) # 모든 Profile 객체에 대한 업데이트 
        self.stdout.write(self.style.SUCCESS("✅ 모든 사용자의 ranking_score가 0으로 초기화되었습니다.")) # 디버깅용
