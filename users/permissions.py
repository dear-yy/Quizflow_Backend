from rest_framework import permissions

# 프로필의 소유자만 수정할 수 있도록 하는 커스텀 권한 로직
class CustomReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        '''
        조회 -> 모두 허용 
        그외 -> 와 요청 객체 유저와 일치하는 접근 유저(요청 객체 주인만) 허용
        '''
        if request.method in permissions.SAFE_METHODS: # GET 등의 (데이터 영향 X)요청
            return True # 권한 부여 
        # PUT, PATCH 등의 (데이터 영향 O)요청
            # request.user: 로그인된 사용자로,토큰이 유효한지 여부를 담고있음
        return obj.user == request.user # 접근 객체(obj) 유저와 요청 객체(request) 유저가 일치하면(True) 권한 부여