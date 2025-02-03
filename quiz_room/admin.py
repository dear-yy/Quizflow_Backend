from django.contrib import admin
from .models import Quizroom, QuizroomMessage

# Register your models here.

# QuizroomMessage 모델을 Quizroom 모델에 인라인으로 등록
class QuizroomMessageInline(admin.TabularInline):  # 또는 admin.StackedInline
    model = QuizroomMessage
    extra = 0  # 기본 메시지 추가 항목 수 # (사용자가 실제로 메시지를 추가해야 할 경우에만 폼을 표시 -> 불필요한 빈 폼을 방지)

    # quizroom 필드 설정
    def save_model(self, request, obj, form, change):
        #  참조되는 모델 Quizroom 모델 객체의 inline으로 설정
        if not obj.quizroom: 
            obj.quizroom = self.instance
        obj.save()

# Quizroom 모델을 관리자 페이지에 등록
class QuizroomAdmin(admin.ModelAdmin):
    inlines = [QuizroomMessageInline]  # QuizroomMessage를 인라인으로 등록

admin.site.register(Quizroom, QuizroomAdmin)
admin.site.register(QuizroomMessage)  # QuizroomMessage 객체만 보고 싶다면 등록하기