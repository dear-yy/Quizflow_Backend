import os
import sys
import openai
import time
import json
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple
from django.conf import settings
from django.contrib.auth.models import User
from quiz_room.models import Article

# Django 프로젝트 절대 경로로 추가
# 두 단계 위로 올라가서 루트 디렉토리(myquiz/)에 접근
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))  # __file__ : 현재 경로
# DJANGO_SETTINGS_MODULE 환경 변수를 설정하여 Django 설정을 로드합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myquiz.settings')

# 키 설정 
openai.api_key = settings.OPENAI_API_KEY 
GOOGLE_SEARCH_ENGINE_ID  = settings.GOOGLE_SEARCH_ENGINE_ID
GOOGLE_API_KEY = settings.GOOGLE_API_KEY


'''
get_keywords_from_feedback
    - extract_keywords
'''

def get_keywords_from_feedback(recent_user_feedback:str, user_feedback_list:list, keyword_list:list) -> Tuple[List[str], str]:
    # 1. 새로운 키워드 추출
    new_keyword_list = extract_keywords(False, user_feedback_list)

    # 2. 추출 키워드 kewords_list에 연결(누적 키워드 리스트 -> 검색쿼리)
    search_query = " ".join(new_keyword_list)

    return (new_keyword_list, search_query)

# 키워드 추출
def extract_keywords(retry:bool, user_feedback_list:str, max_keywords:int=3) -> List:
    fail_cnt = 0  # 실패 카운트 초기화
    recent_user_feedback = user_feedback_list[-1]
    while fail_cnt < 3:
        try:
            # SEO 최적화된 키워드란 -> 검색 엔진에서 사람들이 자주 검색하는 단어( 많은 사람들이 검색할 가능성이 높은은 키워드)
            system_prompt = f"""
                당신의 역할은 **사용자 피드백을 바탕으로 SEO(검색 엔진 최적화)에 최적화된 키워드 3개를 생성**하는 것입니다.

                # 1 키워드 생성 전략:
                    - 가장 최근 피드백({recent_user_feedback})을 **중심으로** 삼아,
                      그 의미를 더 구체화하고 확장할 수 있는 키워드를 생성하세요.
                    - 과거 피드백 리스트({user_feedback_list})의 요소들을 함께 고려하여
                      **최근 피드백과 의미적으로 연결**하거나 **심화된 방향**으로 발전시킬 수 있는 키워드를 생성하세요.
                      예: 과거 피드백="환경 오염", 가장 최근 피드백="산불" → 생성 키워드: `"산불 원인"`, `"환경 오염 피해 사례"`, `"기후변화 산불"`
                    - {retry}가 True이면, 기존 키워드로 아티클 검색에 실패한 상황이므로 피드백을 기반으로 검색 결과가 존재할만한 더 포괄적인 키워드로 생성하세요. 

                # 2 키워드 추출 규칙:
                    - 생성하는 키워드는 **검색 엔진에서 자주 검색될 가능성이 높은** **명사 중심의 구체적 표현**이어야 합니다.
                    - 명확하고 검색 친화적인 단어로 구성하세요.
                    - 가능한 한 **사용자의 최신 피드백({recent_user_feedback})**을 가장 우선적으로 반영하세요.
  
                # 3 피드백 유효성 판단 및 처리:
                    - 만약 {recent_user_feedback}이 무의미한 입력 (예: "ㅁㅇ니러", "모르겠다", "아무거나")일 경우:
                        1. 전체 피드백 리스트 {user_feedback_list}를 **최신순(인덱스가 큰 순서대로)**으로 탐색하여 의미 있는 내용을 중심으로 키워드를 생성하세요.
                        2. 만약 {user_feedback_list}가 비어있거나 모든 요소가 무의미한 문자열인 경우:
                    - ["역사", "철학", "과학", "예술", "기술", "문화", "건강"] 중 하나의 주제를 임의로 선택하여 관련 키워드를 생성하세요.

                # 4 출력 형식:
                    - 결과는 JSON 형식으로 출력하세요.
                        예시: {{"k1":"키워드1", "k2":"키워드2", "k3":"키워드3"}}
            """

            # Open API 호출
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "system 지침에 따라 최근 사용자 피드백을 중심으로 SEO 최적화 키워드 3개를 생성해주세요."},
                ],
                temperature=0,
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
                print(f"⚠️ [extract_keywords] JSON 파싱 오류: {e}. 응답 내용: {response['choices'][0]['message']['content']}")
                continue  # 재시도
            return keywords_list # 정상 추출
        except openai.error.RateLimitError:
            fail_cnt += 1
            print("🔍 Rate limit에 도달했습니다. 40초 후 재시도합니다...")
            time.sleep(40)
        except Exception as e:
            fail_cnt += 1
            print(f"🔍 Error during OpenAI API call: {e}")

    print("⚠️ 3번 이상의 실패로 키워드 추출 프로세스를 종료합니다.")
    return []  # 3번 이상 실패하면 빈 리스트 반환






'''
    select_article
        - Google_API
        - process_recommend_article
            - find_recommend_article
            - get_article_body
            - Google_API(재요청 시)
        
'''
def select_article(user:User, query:str, user_feedback_list:list) -> Dict: # (사용자 객체, 누적 키워드, 누적 피드백)
    fail = 0                    
    retry_extracted_keywords = None # 키워드 재추출 시
    num_results_per_site = 3    # 사이트당 결과 개수
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
        # 추가하기
    ]
    recommend_article_title, recommend_article_body, recommend_article_url, recommend_article_reason = "실패", "실패", "실패", "실패"

    # 1. 후보 기사 목록 서치 (추출된 키워드 기반 쿼리로)
    df = Google_API(user, query, num_results_per_site, sites)  # 후보 기사 목록
    time.sleep(10)  # 생성 토큰 제한 에러 예방
    
    # 2. 추천 아티클 결정 
    while fail<3 :
        # 아티클 추천 gpt 요청
        info_for_the_article = process_recommend_article(df, user_feedback_list) 

        if info_for_the_article is None: # 아티클 추천 실패
            fail += 1
            # 키워드 재추출 -> 검색 쿼리 재구성
            retry_extracted_keywords = extract_keywords(True, user_feedback_list, max_keywords=3)
            if retry_extracted_keywords:
                query = " ".join(retry_extracted_keywords) # 검색 쿼리 재구성
                df = Google_API(user, query, num_results_per_site=5, sites=sites) # # 후보 기사 목록 재구성
        else: # 아티클 추천 성공
            # Title, URL 및 Body 추출
            recommend_article_title = info_for_the_article["Title"]
            recommend_article_body = info_for_the_article["Body"]
            recommend_article_url = info_for_the_article["URL"]
            recommend_article_reason = info_for_the_article["Reason"]
            print("✅ 추천 아티클 URL:", recommend_article_url)
            break  # 본문 추출 성공 시 루프 종료
    
    # 3. 최종 추천 아티클 정보 반환
    return  {
        "title": recommend_article_title,
        "body": recommend_article_body, 
        "url": recommend_article_url, 
        "reason": recommend_article_reason, 
        "retry_extracted_keywords": retry_extracted_keywords # 키워드 재추출시, DB에 반영하기 위함 
    }



# 후보 기사 정보 ("Title", "Description", "Link", "Domain") 형식
def Google_API(user:User, query:str, num_results_per_site:int, sites:list[str]) -> pd.DataFrame: # DataFrame:2차원 행&열 데이터 구조
    # 후보 기사 리스트
    df_google_list = [] 
    # 사용자 과거 아티클 내역 
    past_articles = set(Article.objects.filter(user=user).order_by('-timestamp')[:100].values_list('url', flat=True)) # user의 과거 아티클을 최신순으로 정렬 후, 상위 100개 반환(중복은 삭제)

    # 사이트 별 후보 기사
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
                        print(f"🔍 '{site}'에 {site_query}에 대한 관련 검색 결과가 없습니다.")
                        break 

                # 4. 기사 정보 추출
                for search_item in search_items: 
                    # 결과 개수 체크
                    if collected_results_cnt >= num_results_per_site: # 결과 개수 도달
                        break # for 루프 종료

                    # 정보 추출
                    link, title, description = search_item.get("link"), search_item.get("title"), search_item.get("snippet")

                    # 사용자 과거 아티클과 중복 방지
                    if link in past_articles:
                        continue  

                    # 추가 조건: m.khan.co.kr 처리
                    if site == "khan.co.kr" and "m.khan.co.kr" in link:
                        link = link.replace("m.khan.co.kr", "khan.co.kr") # (모바일 링크 -> 일반 웹사이트 링크)변환

                    # 기사 정보에 대한 DataFrame 생성 후 리스트에 추가
                    df_google_list.append( pd.DataFrame(
                            [[title, description, link, site]], # 다음 행 추가(하나의 리스트로 묶어 1개의 행 구성)
                            columns=["Title", "Description", "Link", "Domain"], # 열 정보
                    )   )
                    collected_results_cnt += 1  # 수집 결과 개수 증가
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
def process_recommend_article(df:pd.DataFrame=None, user_feedback:str="") -> Dict:
    # 초기화
    fail = 0

    # 추천 아티클 선정 후, body 추출 프로세스
    while fail < 3:
        # 1. 추천 아티클 반환
        recommend_article, reason = find_recommend_article(df, user_feedback) 

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
            return { "Title": title, "URL": url, "Body": article_body, "Reason": reason }
    
    # 정보 추출 실패 시
    return None
    


# 추천 아티클 결정#
def find_recommend_article(df_google:pd.DataFrame, user_feedback_list:list) -> Tuple[Dict, str]:
    fail = 0
    # DataFrame의 각 항목 리스트 형태로 변환해 저장
    article_descriptions = df_google["Description"].tolist()
    article_indices = df_google.index.tolist()
        

    while fail < 3:  
        try:
            # Open API 호출         # 토큰 초과 에러 발생해서, title 정보는 프롬프트에서 제외함!
            system_prompt = f"""
            # 지시문
                - 당신은 사용자의 피드백과 아티클 설명을 기반으로
                  사용자에게 적합한 아티클을 추천하는 어플리케이션의 역할을 한다.
            # 추천 조건
                1. 최신 피드백(리스트에서 인덱스가 높은 순서)을 우선적으로 고려하세요.
                2. 최신 피드백이 다루는 주제와 가장 관련이 있는 아티클을 선택하세요.
                3. 제목과 설명을 기반으로 아티클의 적합성을 판단하세요.
                4. 단순 뉴스 보도, 광고성 내용, 또는 중복된 내용은 제외하세요.
                5. 지식적인 설명 또는 학습에 도움을 줄 수 있는 내용이 포함되어야 한다.

            # 출력 형식
              - 답변은 딕셔너리 형태로 반환하세요. 
              - 딕셔너리 key 이름은 "index"와 "reason"으로 설정하세요.
              - "reason" key의 value에 해당하는 문자열 내부에서 작은따옴표(')와 큰따옴표(")가 등장하지 않도록 문자열을 구성하세요.
              - "reason" key의 value는 2문장 정도의 한국어로 출력하세요.
                예:
                ```
                    {{"index": "추천된 아티클의 고유 index", "reason": "왜 이 아티클이 적합한지 간단히 설명" }}
                ```
            """
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    { "role": "system", "content": system_prompt,},
                    {   "role": "user",
                        "content": (
                            f"사용자 피드백: {user_feedback_list}\n\n"
                            "아티클 목록 (index 포함):\n"
                            + "\n".join(
                                f"{i}. [Index: {idx}]  아티클 설명: {description}\n  "
                                for i, (idx, description) in enumerate(
                                    zip(article_indices, article_descriptions,)
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
            # (JSON -> 딕셔너리) 변환 작업
            content = re.sub(r'"reason":\s*"([^"]*?)"', escape_inner_quotes, content)
            try:
                content_dict = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"⚠️ [find_recommend_article] JSON 파싱 오류: {e}. 응답 내용: {response['choices'][0]['message']['content']}")
                fail += 1 
                continue

            # content 존재 검증
            if not isinstance(content_dict["index"], int): 
                break
            elif not isinstance(content_dict["reason"], str) or not content_dict["reason"]: # 타입과 존재 여부
                break

            # 정수 index 저장 
            recommended_index = int(content_dict["index"])  
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
            reason = content_dict["reason"]
            return (recommended_article, reason) # 결과 DataFrame 형태로 반환

        except openai.error.RateLimitError:
            print("🔍 Rate limit reached. Retrying in 40 seconds...")
            fail += 1
            time.sleep(40)  # 40초 지연 후 재시도
            continue 

    return (None, "") # 처리 실패시 
    


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

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"}

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



# 정규식: "key": "value"
# key나 전체 구조에 있는 큰따옴표는 건드리면 안 되므로 value 내부만 바꿔야 함
def escape_inner_quotes(match):
    inner = match.group(1)
    escaped = re.sub(r'"', r'\\"', inner)  # 큰따옴표 escape
    return f'"reason": "{escaped}"'