- 파이썬 → [python 3.12.6](https://www.python.org/downloads/release/python-3126/)
    
    `python -V`   * 대문자 V
    
- 장고 → 5.1.5
    
    `pip show django`
    
- DRF → 3.15.2
    
    `pip show djangorestframework`

[가상환경 셋팅]
1. C드라이브 위치에서 venvs라는 가상 환경 관리용 폴더 생성
2. venvs 폴더에 가상 환경  생성 
    ```cd venvs```
    ```python -m venv  {가상 환경 이름}```
3. 가상환경 활성화
   ```cd C:\venvs\{가상 환경 이름}\Scripts```
   ```activate```
4. 백엔드 프로젝트 폴더 위치로 이동 
5. 마이그레이션 (초기 DB생성)
6. 관리자 생성
   ```python manage.py createsuperuser```
7. 서버 실행
   ```python magage.py runserver```

[migration 순서]
- 앱 간 의존성 문제로 users앱 admin보다 먼저 migrate되어야 함
  1. ```python manage.py makemigrations users```
  2. ```python manage.py migrate``` 
