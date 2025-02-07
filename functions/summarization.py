# 윤서 -> 아티클 body 요약 구현 
import openai
import time
from quiz_room.models import Article  # Article 모델 import

def split_text(text, max_chunk_size=3000):
    """
    긴 텍스트를 max_chunk_size 크기로 분할합니다.
    """
    chunks = []
    while len(text) > max_chunk_size:
        split_point = text.rfind('.', 0, max_chunk_size)  # 문장 단위로 자르기
        if split_point == -1:
            split_point = max_chunk_size
        chunks.append(text[:split_point + 1].strip())
        text = text[split_point + 1:].strip()
    chunks.append(text)
    return chunks

def summarize_chunk(chunk, model="gpt-4o-mini", max_tokens=150):
    prompt = f"""
        다음 텍스트를 기반으로 전체 기사 내용을 요약하고 주요 정보를 포함하세요. 요약은 5~7개의 문장으로 작성해주세요.
        기사의 전체 맥락을 유지하며 핵심 내용을 간결히 정리하세요.
        
        텍스트 조각: {chunk}
        """
    while True:
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an assistant that summarizes text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0
            )
            return response['choices'][0]['message']['content'].strip()
        except openai.error.RateLimitError:
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)
        except Exception as e:
            return f"Error: {e}"

def summarize_article(article_text):
    """
    긴 텍스트를 요약하는 함수입니다.
    """
    chunks = split_text(article_text)
    partial_summaries = [summarize_chunk(chunk) for chunk in chunks]
    
    final_prompt = """
    다음 텍스트를 기반으로 전체 기사 내용을 요약하고 주요 정보를 포함하세요.
    기사의 전체 맥락을 유지하며 핵심 내용을 간결히 정리하세요.
    변화 추이가 있을 경우, 직접적인 수의 나열보다는 단어로 표현하세요.
    요약은 대략 10개의 문장으로 작성해주세요.
    
    """ + "\n\n".join(partial_summaries)
    
    while True:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an assistant that summarizes text."},
                    {"role": "user", "content": final_prompt}
                ],
                max_tokens=1000,
                temperature=0
            )
            return response['choices'][0]['message']['content'].strip()
        except openai.error.RateLimitError:
            print("Rate limit reached. Retrying in 40 seconds...")
            time.sleep(40)
        except Exception as e:
            return f"Error: {e}"

def update_article_summary(article_id):
    """
    주어진 article_id를 가진 Article 객체의 body 필드를 요약하여 업데이트하는 함수
    """
    try:
        article = Article.objects.get(id=article_id)
        summary = summarize_article(article.body)
        article.body = summary  # 기존 body 필드를 요약된 내용으로 업데이트
        article.save()
        print(f"Article {article_id} 요약 완료.")
    except Article.DoesNotExist:
        print(f"Article {article_id}을 찾을 수 없습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")