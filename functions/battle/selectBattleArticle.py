import os
import sys
import openai
import time
import json
import requests
import random
import django
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple
from django.conf import settings
from django.contrib.auth.models import User
from quiz_room.models import Article # 각 사용자의 과거 아티클 중복 제거

# Django 프로젝트 절대 경로로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..') )) # __file__ : 현재 경로

# DJANGO_SETTINGS_MODULE 환경 변수를 설정하여 Django 설정을 로드합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myquiz.settings')

# 키 설정 
openai.api_key = settings.OPENAI_API_KEY 
GOOGLE_SEARCH_ENGINE_ID  = settings.GOOGLE_SEARCH_ENGINE_ID
GOOGLE_API_KEY = settings.GOOGLE_API_KEY


'''
extract_keywords
'''

# 랜덤 키워드 추출
def extract_keywords() -> Tuple[List, str]:
    max_keywords=1  # 최대 추출 키워드 수 설정
    fail_cnt = 0  # 실패 카운트 초기화
    categories = [
        # 사회
        "제도", "권력", "계층", "문화", "경제", "정치", "공동체", "노동", "교육", "법",
        "복지", "기술", "미디어", "환경", "젠더", "가족", "범죄", "윤리", "이주", "세계화",
    
        # 과학
        "자연", "우주", "생명", "에너지", "물질", "기술", "실험", "진화", "환경", "수학",
        "화학", "물리학", "생물학", "지구과학", "천문학", "인공지능", "유전", "신경과학", "전자기", "방사능",
    
        # 역사
        "문명", "국가", "전쟁", "혁명", "산업", "사회", "문화", "정치", "경제", "교류",
        "종교", "왕조", "제국", "무역", "탐험", "식민지", "독립", "세계사", "민족", "외교",
    
        # 철학
        "존재", "인식", "진리", "윤리", "논리", "인간", "자유", "경험", "사상", "가치",
        "신념", "도덕", "언어", "정의", "실재", "이성", "감성", "근대성", "초월", "목적",
    
        # 종교
        "신앙", "신화", "경전", "의례", "신성", "구원", "영성", "신학", "교리", "초월",
        "창조", "예배", "기도", "성직", "신비", "계시", "신념", "윤리", "내세", "성스러움",
    
        # 예술
        "미학", "표현", "창작", "감정", "형식", "상징", "아름다움", "영감", "조화", "상상력",
        "색채", "공간", "움직임", "소리", "조형", "서사", "해석", "독창성", "스타일", "패턴"
    ]
    random_category = random.choice(categories)
    print("🔍 랜덤 카테고리:", random_category)

    while fail_cnt < 3:
        try:
            system_prompt = f"""
            당신의 역할은 SEO(검색 엔진 최적화)에 최적화된 키워드를 생성하는 것입니다.
            1. **키워드 생성 조건**:
              - 카테고리는 {random_category}입니다.
              - 이 카테고리와 관련된 교양 지식 습득에 유용한 키워드를 생성하세요.
              - 키워드 생성 시 고려해야 할 사항:
                - **정보성**: 사람들이 학습하거나 탐구하고자 할 때 유용한 키워드를 생성하세요.
                - **검색 가능성**: 사람들이 검색할 가능성이 높은 단어를 기반으로, 타겟 사용자가 궁금해할만한 키워드를 고려해야 합니다. 검색 가능성을 위해서 가능한 구체적이진 않고 일반적이고 포괄적인 키워드를 사용하세요.
            2. **키워드 생성 규칙**:
              - 검색 엔진에서 자주 검색될 가능성이 높은 단어를 선택하세요.
              - 명사 중심의 구체적이고 직관적인 키워드를 사용하세요.
              - 동일한 단어나 중복된 키워드는 제외하세요.
              - 키워드의 개수는 {max_keywords}개 입니다

            3. **출력 형식**:
              - 추출된 키워드들은 딕셔너리 형태의 JSON 형식으로 반환하세요. 
              - 키워드 개수에 맞게 딕셔너리를 구성하세요.
                예:
                ```
                  {{"k1":"키워드1", "k2":"키워드2", "k3":"키워드3", ...}}
                ```
            """

            # Open API 호출
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    { "role": "user",
                      "content": ("키워드를 생성해주세요."),
                    },
                ],
                temperature=0.5, # 일관성
                max_tokens=2048,
                top_p=1, # 추출 단어의 관련성 제어
                frequency_penalty=0, # 반복되는 단어를 제어(고려)
                presence_penalty=0, # 새로운 단어를 제어(고려)
            )

            # GPT의 응답 분석 
            keywords = response["choices"][0]["message"]["content"]

            # (JSON -> 딕셔너리) 변환
            keywords = keywords.replace("'", "\"") # JSON 형식에 맞게 수정
            try:
                keywords_dict = json.loads(keywords)
                keywords_list = list(keywords_dict.values()) # (딕셔너리 value -> 리스트) 변환
            except json.JSONDecodeError as e:
                fail_cnt += 1
                print(f"🔍 JSON 파싱 오류: {e}. 응답 내용: {response['choices'][0]['message']['content']}")
                continue  # 재시도: while문 처음부터

            query = " ".join(map(str, keywords_list))
            print("🔍 추출된 키워드:", keywords_list) # 디버깅 
            # 추출된 키워드 리스트 반환 
            return (keywords_list, query)
        
        except openai.error.RateLimitError:
            fail_cnt += 1
            print("🔍 Rate limit에 도달했습니다. 40초 후 재시도합니다...")
            time.sleep(40)
        except Exception as e:
            print(f"🔍 Error during OpenAI API call: {e}")
            return ([], "")
        
        print("⚠️ 3번 이상의 실패로 키워드 추출 프로세스를 종료합니다.")
        return ([],"")  # 3번 이상 실패하면 빈 리스트 반환





'''
    select_article
        - Google_API
        - process_recommend_article
            - get_article_body
            - find_recommend_article
            - Google_API
        
'''
# 사용자 입력 
def select_article(player_1:User, player_2:User, query:str) -> Dict:
    fail = 0                    
    retry_extracted_keywords = None # 키워드 재추출 시
    num_results_per_site = 3    # 각 사이트당 결과 개수
    sites = [                   # 검색 가능 사이트 목록 
        # "brunch.co.kr",
        "bbc.com",
        "khan.co.kr",
        "hani.co.kr",
        "ytn.co.kr",
        "sisain.co.kr",
        "news.sbs.co.kr",
        "h21.hani.co.kr",
        "ohmynews.com",
    ]

    # 1. 후보 기사 목록 서치 (추출된 키워드 기반 쿼리로)
    df = Google_API(player_1, player_2, query, num_results_per_site, sites)  # query로 탐색된 기사 목록
    time.sleep(20)  # 생성 토큰 제한 에러 예방

    
    # 2. 추천 아티클 결정 
    while fail < 3:
        # 아티클 추천 gpt 요청
        info_for_the_article = process_recommend_article(df, query)
        
        if info_for_the_article is None : # 아티클 추천 실패
            fail += 1
            # 키워드 재추출 -> 검색 쿼리 재구성
            retry_extracted_keywords = extract_keywords()
            if retry_extracted_keywords:
                query = " ".join(retry_extracted_keywords) # 검색 쿼리 재구성
                df = Google_API(player_1, player_2, query, num_results_per_site=5, sites=sites) # 후보 기사 목록 재구성
        else: # 추천 아티클이 존재한다면
            # Title, URL 및 Body 추출
            recommend_article_title = info_for_the_article["Title"]
            recommend_article_body = info_for_the_article["Body"]
            recommend_article_url = info_for_the_article["URL"]
            print("✅ 추천 아티클 URL:", recommend_article_url)
            break  # 본문 추출 성공 시 루프 종료
    
    # 3. 최종 추천 아티클 정보 반환
    return  {
        "title": recommend_article_title,
        "body": recommend_article_body, 
        "url": recommend_article_url, 
        "retry_extracted_keywords": retry_extracted_keywords # 키워드 재추출시, DB에 반영하기 위함 
    }


        



# 후보 기사 정보 ("Title", "Description", "Link", "Domain") 형식
def Google_API(player_1:User, player_2:User, query:str, num_results_per_site:int, sites:list[str]) -> pd.DataFrame: # DataFrame:2차원 행&열 데이터 구조
     # 후보 기사 리스트
    df_google_list = [] 

    # 사용자의 과거 아티클 정보
    player_1_past_articles = set(Article.objects.filter(user=player_1).order_by('-timestamp')[:100].values_list('url', flat=True)) # player_1의 과거 아티클을 최신순으로 정렬 후, 상위 100개 반환(중복은 삭제)
    player_2_past_articles = set(Article.objects.filter(user=player_2).order_by('-timestamp')[:100].values_list('url', flat=True)) # plaeyr_2의 과거 아티클을 최신순으로 정렬 후, 상위 100개 반환(중복은 삭제)
    past_articles = player_1_past_articles.union(player_2_past_articles)

    # 사이트 별 쿼리로 후보 기사 조회
    for site in sites: 
        # 1. Google Custom Search API에 대한 요청 URL 구성
        site_query = f"site:{site} {query}"     # 각 사이트 별 검색어 구성
        collected_results_cnt = 0               # 수집한 결과 개수
        start_index = 1                         # 검색 결과에서 탐색 시작 위치
        num = 5                                 # 한 번에 반환할 결과의 개수
        url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_SEARCH_ENGINE_ID}&q={site_query}&start={start_index}&num={num}" 
            
        while collected_results_cnt < num_results_per_site: # 정해진 개수에 도달할 때까지
            try:
                # 2. URL로 HTTP GET 요청
                response = requests.get(url)

                # 3. 요청 성공 여부에 따른 처리 
                if response.status_code != 200: # 요청 실패
                    print(f"⚠️ {site}에 대한 HTTP GET 요청 실패: {response.status_code}, Message: {response.text}")
                    break 
                else: # 요청 성공 
                    data = response.json() # 응답 데이터 -> JSON 형식
                    search_items = data.get("items") # 검색 결과 항목(기사)들 가져오기
                    if not search_items: # 검색 결과가 없으면
                        print(f"🔍 '{site}'에 관련 검색 결과가 없습니다.")
                        break 

                # 4. 기사 정보 추출
                for search_item in search_items:
                    # 결과 개수 체크
                    if collected_results_cnt >= num_results_per_site: # 결과 개수 도달
                        break # for 루프 종료

                    # 정보 추출
                    link, title, description = search_item.get("link"), search_item.get("title"), search_item.get("snippet")

                    # 사용자 과거 아티클과의 중복 방지
                    if link in past_articles:
                        continue  

                    # 추가 조건: m.khan.co.kr 처리
                    if site == "khan.co.kr" and "m.khan.co.kr" in link:
                        link = link.replace("m.khan.co.kr", "khan.co.kr") # (모바일 링크 -> 일반 웹사이트 링크)변환

                    # 기사 정보에 대한 DataFrame 생성 후 리스트에 추가
                    df_google_list.append(
                        pd.DataFrame(
                            [[title, description, link, site]], # 다음 행 추가(하나의 리스트로 묶어 1개의 행 구성)
                            columns=["Title", "Description", "Link", "Domain"], # 열 정보
                        )
                    )
                    collected_results_cnt += 1  # 현재 수집 결과 개수 증가
            except Exception as e:
                print(f"⚠️ Error occurred for site {site}: {e}")
                break
    # 5. 모든 결과를 하나의 DataFrame으로 결합
    if df_google_list: 
        df_google = pd.concat(df_google_list, ignore_index=True)  # ignore_index=True: 새로운 연속적인 인덱스를 부여
    else:  # df_google_list가 비어있다면
        df_google = pd.DataFrame(columns=["Title", "Description", "Link", "Domain"]) # 빈 DataFrame 

    return df_google



# gpt 기반 아티클 추천 후, body 정보 추출하여 추천 기사 정보 반환환 
    # 추천된 아티클이 없거나 본문을 가져올 수 없을 경우, 해당 데이터를 삭제 후 재추천
def process_recommend_article(df:pd.DataFrame=None, query:str="") -> Dict:
    # 초기화
    fail = 0

    # 추천 아티클 선정 후, body 추출 프로세스
    while fail < 3:
        # 1. 추천 아티클 반환
        recommend_article =  find_recommend_article(df, query) 

        # 2. 아티클 존재 여부 파악
        if recommend_article is None: # 추천 아티클 존재 X
            if df.empty: # 후보 기사 목록이 빈 경우
                print("⚠️ 후보 기사 목록이 비어 추천할 수 있는 기사가 없습니다.")
                break
            else: 
                fail += 1
                continue # 재추천
        else: # 추천 아티클 존재 O
            url = recommend_article["Link"] 
            domain = recommend_article["Domain"]
            title = recommend_article["Title"]

        # 3. 본문 추출
        article_body = get_article_body(url, domain)
        
        if ( not article_body or len([s for s in article_body.split(".") if s.strip()]) <= 5 ): # 본문이 없거나 5문장 이하인 경우
            print(f"🔍 본문이 없는 아티클 (또는 본문이 5문장 이하)이므로 데이터를 추출할 수 없습니다.")
            df.drop(df[df["Link"] == url].index, inplace=True) # df(후보 기사 목록)에서 삭제
            fail += 1
            continue   # 재추천
        else: # 추출 성공
            return { "Title": title, "URL": url, "Body": article_body}
    
    # 정보 추출 실패 시
    return None
    


# 추천 아티클 결정#
def find_recommend_article(df_google:pd.DataFrame, query:str="") -> Dict:
    fail = 0
    # DataFrame의 각 항목 리스트 형태로 변환해 저장
    article_descriptions = df_google["Description"].tolist()
    article_indices = df_google.index.tolist()

    while fail < 3:
        try:
            # Open API 호출
                # 토큰 초과 에러 발생해서, title 정보는 제외함!
            system_prompt = f"""
            # 지시문
                - 당신은 아티클의 키워드인 query와 아티클의 설명을 기반으로 사용자에게 적합한 아티클을 추천하는 어플리케이션의 역할을 한다.
            # 추천 조건
                1. query에서 다루는 주제와 관련이 있는 아티클을 선택하세요.
                2. 제목과 설명을 기반으로 아티클의 적합성을 판단하세요.
                3. 단순 뉴스 보도, 광고성 내용, 또는 중복된 내용은 제외하세요.
                4. 지식적인 설명 또는 학습에 도움을 줄 수 있는 내용이 포함되어야 한다.

            # 출력 형식
              - index 번호만 출력하세요
                예:
                ```
                    6
                ```
            """
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": (
                            f"query: {query}\n\n"
                            "아티클 목록 (index 포함):\n"
                            + "\n".join(
                                f"{i}. [Index: {idx}]  설명: {description}\n  "
                                for i, (idx, description) in enumerate(
                                    zip(
                                        article_indices,
                                        article_descriptions,
                                    )
                                )
                            )
                        ),
                    },
                ],
                temperature=0,
                max_tokens=2048,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )


            # GPT의 응답 분석 
            content = response["choices"][0]["message"]["content"]

            # 정수형으로 변환 시도
            try:
                recommended_index = int(content)  # 문자열을 정수로 변환
            except ValueError:
                recommended_index  = 0  # 변환 실패 시 기본값 설정

            # index가 DataFrame에 존재하는지 확인
            if recommended_index not in df_google.index:
                print(f"⚠️ 추천된 index({recommended_index})는 존재하지 않습니다.")
                break

            # 해당 index로 행(해당 기사 정보) 반환
            recommended_row = df_google.loc[recommended_index]
            recommended_article = {
                "Link": recommended_row["Link"],
                "Domain": recommended_row["Domain"],
                "Title": recommended_row["Title"]
            }
            return recommended_article
        except openai.error.RateLimitError:
            print("🔍 Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)  # 40초 지연 후 재시도
            fail += 3
            continue

    return None # 처리 실패 시
    

def get_article_body(url:str, domain:str) -> str:
    # 본문 추출을 위한 사이트별 태그 정보#
    SITE_CLASS_MAPPING = {
        # "brunch.co.kr": [{"tag": "div", "class": "wrap_body"}],
        "bbc.com": [{"tag": "main", "class": "bbc-fa0wmp"}],
        "khan.co.kr": [{"tag": "div", "class": "art_body"}],
        "hani.co.kr": [{"tag": "div", "class": "article-text"}],
        "ytn.co.kr": [{"tag": "div", "class": "vodtext"}],
        "sisain.co.kr": [{"tag": "div", "class": "article-body"}],
        "news.sbs.co.kr": [{"tag": "div", "class": "main_text"}],
        "h21.hani.co.kr": [{"tag": "div", "class": "arti-txt"}],
        "ohmynews.com": [
            {"tag": "article", "class": "article_body at_contents article_view"},
            {"tag": "div", "class": "news_body"},
        ],
        # 공백 주의 # 추가 도메인 및 태그/클래스 매핑
        # 한국일보, mbcnews는 제외
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    }

    try:
        # URL에서 HTML (요청)가져오기
        response = requests.get(url, headers=headers)
        response.raise_for_status() # 오류 발생하면, 예외 발생
        soup = BeautifulSoup(response.text, "html.parser")

        # 도메인이 제공된 경우 SITE_CLASS_MAPPING에서 처리
        site_info = SITE_CLASS_MAPPING.get(domain)
        if not site_info: # 해당 도메인에 대한 정보가 없는 경우 
            return None

        # 모든 매핑 리스트 순회하며 태그/클래스 처리
        for mapping in site_info:
            tag_name = mapping.get("tag")
            class_name = mapping.get("class")
            main_body = soup.find(tag_name, class_=class_name)
            if main_body:
                # 태그 내부에 p, h1 등이 있는 경우와 없는 경우 처리
                text_elements = main_body.find_all(["h1", "h2", "h3", "h4", "p", "li"])
                # <p> 태그 개수 확인 (2개 이하이면 본문이 부족하다고 간주)

                paragraph_count = len(main_body.find_all("p"))
                if paragraph_count <= 2:
                    return main_body.get_text(strip=True)

                if text_elements:
                    return "\n".join(
                        [element.get_text(strip=True) for element in text_elements]
                    )
                else:
                    return main_body.get_text(strip=True)
        # 해당 도메인에 매핑된 태그와 클래스를 찾을 수 없는 경우 
        return None 
    except requests.exceptions.RequestException as e: # HTTP 요청 오류
        return None
    except Exception as e: # 본문 추출중 오류
        return None

