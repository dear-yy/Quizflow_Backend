from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin # admin 페이지에서 User 관리를 위한 클래스
from django.contrib.auth.models import User
from .models import Profile

# Register your models here.

# 관리자 페이지에서 User 모델과 연결된 Profile 모델을 함께 관리할 수 있도록 확장하여 등록 
# Inline: 연결된 모델 데이터를 함께 보여주고 관리할 수 있도록 만드는 도구

# 1. Profile 모델을 연결된 User 모델의 Inline으로 포함되도록 정의 
    # User를 관리할 때 Profile 데이터도 같은 페이지에서 관리할 수 있게 만드는 설정
class ProfileInline(admin.StackedInline):
    model = Profile  # Inline으로 표시할 모델 설정
    can_delete = False  # 관리자 Profile 객체를 삭제 권한 비활성(User 모델은 그대로 두고 Profile만 삭제하는 경우를 방지
    verbose_name_plural = "Profile"  # 관리자 페이지에서 보여질 이름 설정


# 2. ProfileInline을 추가하여 기본 UserAdmin 클래스를 확장
    # User 관리 페이지를 열면, Profile에 대한 입력칸도 함께 추가
class UserAdmin(BaseUserAdmin):  # 기본 UserAdmin을 상속받아 확장
    inlines = (ProfileInline, )  # 튜플 형식 (,)!
    list_display = ('id', 'username', 'email')

# 3. 기존 User 모델의 기본 UserAdmin 등록 취소 후, 새롭게 확장한 UserAdmin 등록
admin.site.unregister(User)  # Django 기본 User 모델의 기본 UserAdmin 등록 취소
admin.site.register(User, UserAdmin)  # User 모델에 확장된 UserAdmin을 새로 등록