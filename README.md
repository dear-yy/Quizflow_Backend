## [프로젝트 구성]
**루트** -> myquiz <br>
**앱** -> quiz_room / battle / ranking / users <br>

## [프로젝트 구조]
- **myquiz** -> 프로젝트 루트 폴더 
- **quiz_room** -> 퀴즈 기능 앱 폴더
- **battle** -> 배틀 기능 앱 폴더
- **ranking** -> 랭킹 시스템 앱 폴더
- **users** -> 회원 관리 기능 앱 폴더
- **functions** -> Open AI API 사용하는 기능 모듈 폴더
- **media** -> 사용자 프로필 이미지 관리 폴더
- **install_list.txt** -> 설치 모듈&버전 목록 파일
- **reset_ranking.bat** -> 로컬용(Window) django command 실행 파일
- **reset_ranking.sh** -> 배포용(Ubuntu) django command 실행 파일


## [가상환경 셋팅]
1. C드라이브 위치에서 venvs라는 가상 환경 관리용 폴더 생성
2. venvs 폴더에 가상 환경  생성 
    ```cd venvs```
    ```python -m venv  {가상 환경 이름}```
3. 가상환경 활성화
   ```cd C:\venvs\{가상 환경 이름}\Scripts```
   ```activate```
4. 패키지 설치
  ```python -m pip install -r install_list.txt```
5. 백엔드 프로젝트 폴더 위치로 이동
7. 마이그레이션
  ```python manage.py migrate```
  ```python manage.py makemigrations [앱 이름]```
  ```python manage.py migrate```
8. 관리자 생성
   ```python manage.py createsuperuser```
9. 서버 실행
   ```python magage.py runserver```


## [사용 버전 확인]
- 파이썬 → [python 3.12.6](https://www.python.org/downloads/release/python-3126/)
    
    `python -V`   * 대문자 V 
    
- 장고 → 5.1.5
    
    `pip show django`
    
- DRF → 3.15.2
    
    `pip show djangorestframework`

<br>


## [DB 셋팅]
### 1. PostgreSQL 설치
1. [공식 웹사이트](
## [DB 셋팅]
### 1. PostgreSQL 설치
1. (https://www.postgresql.org/)에 접속
2. 운영체제에 맞는 설치 파일 다운로드
3. 설치 도중 `postgres` 사용자 비밀번호 설정

### 2. PostgreSQL 접속
1. 로그인
    ```psql -U postgres```
2. 로그인
    ```psql -U postgres```
3. DB 생성
    ```CREATE DATABASE [DB명] OWNER root;```
4. DB 목록 확인
    ```\l```

<br>)에 접속
2. 운영체제에 맞는 설치 파일 다운로드
3. 설치 도중 `postgres` 사용자 비밀번호 설정

### 2. PostgreSQL 접속
1. 로그인
    ```psql -U postgres```
2. 로그인
    ```psql -U postgres```
3. DB 생성
    ```CREATE DATABASE [DB명] OWNER root;```
4. DB 목록 확인
    ```\l```

<br>

## [ERD]
<img src="https://github.com/dear-yy/CapstoneDesignProject/blob/main/image/ERD.jpg" width="80%" />

<br>

## [API]
### quiz_room
| 설명 | method | API path |
|------|------|------|
| 퀴즈룸 생성 |  HTTP-Post | /quizrooms/ |
| 퀴즈룸 리스트 조회 |  HTTP-Get | /quizrooms/ |
| 퀴즈룸 상세 조회 |  HTTP-Get | /quizroom/<int:quizroom_id>/message_list/  |
| QuizroomConsumer | WS | /chat/<quizroom_id>/ |



### battle
| 설명 | method | API path |
|------|------|------|
| 매칭 대기 | HTTP-Post | /battle/match/|
| 매칭 현황 조회 | HTTP-Get | /battle/match/|
| 매칭 대기 취소 | HTTP-Get | /battle/match/cancel/ |
| 배틀 완료 내역 조회 | HTTP-Get | /battle/list/ |
| 배틀 종료 | HTTP-Patch | /battle/<int: battleroom_id> /disconnect/ |
| 배틀 결과 조회 | HTTP-Get | battle/<int: battleroom_id> /result/ |
| BattleSeupConsumer | WS | /battle/int:battle_room_id/ |
| BattleConsumer | WS | /battle/<int:battle_room_id>/<int:user_pk>/ |


### ranking
| 설명 | method | API path |
|------|------|------|
| 랭킹보드 조회 | HTTP-Get | /ranking /board/ |

### users
| 설명 | method | API path |
|------|------|------|
| 회원가입 | HTTP-Get | /users/register |
| 로그인 | HTTP-Post | /users/login |
| 프로필 수정 | HTTP-Post | /users/profile/<int:pk> |
| 프로필 조회 | HTTP-Get | /users/profile/<int:pk> |
| 회원 탈 | HTTP-Delete | /users/account/delete/ |


