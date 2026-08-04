#!/usr/bin/env python3
"""
네이버 카페 키워드 전용 모니터링 봇
- 3시간 주기 실행
- cafe_history.json으로 중복 알림 방지
"""

import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
import requests
from playwright.sync_api import sync_playwright

# ============================================
# 설정
# ============================================

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 모니터링할 네이버 카페 게시판 및 게시판별 조건 키워드
NAVER_CAFES = [
    {
        "name": "네이버카페 [중앙공기업]",
        "url": "https://cafe.naver.com/f-e/cafes/21737991/menus/193",
        "keywords": ["도시공사", "문화재단", "문화관광재단", "복지재단", "남양주", "구리", "포천", "의정부"]
    },
    {
        "name": "네이버카페 [지방공기업]",
        "url": "https://cafe.naver.com/f-e/cafes/21737991/menus/189",
        "keywords": ["도시공사", "문화재단", "문화관광재단", "복지재단", "남양주", "구리", "포천", "의정부"]
    },
    {
        "name": "네이버카페 [기타기관]",
        "url": "https://cafe.naver.com/f-e/cafes/21737991/menus/232",
        "keywords": ["남양주", "구리", "포천", "의정부", "재단", "공사"]
    }
]

HISTORY_FILE = "cafe_history.json"

# ============================================
# 헬퍼 함수
# ============================================

def get_kst_now():
    """무조건 KST(한국시간) 반환"""
    KST = timezone(timedelta(hours=9))
    return datetime.now(KST)

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print(f"💾 카페 히스토리 저장 완료 ({len(history)}건 기록됨)")
    except Exception as e:
        print(f"❌ 히스토리 저장 실패: {e}")

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정(ENV)이 없습니다.")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        res = requests.post(url, data=data, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")
        return False

def send_safe_telegram_messages(messages_list):
    header = "☕ <b>네이버 카페 새 키워드 글이 등록되었습니다!</b>\n\n"
    footer = f"\n⏰ 확인 시간: {get_kst_now().strftime('%Y-%m-%d %H:%M')} (KST)"
    
    current_chunk = header
    for item in messages_list:
        if len(current_chunk) + len(item) > 3500:
            send_telegram_message(current_chunk)
            time.sleep(1)
            current_chunk = "☕ <b>이어서 전송합니다...</b>\n\n" + item
        else:
            current_chunk += item
            
    current_chunk += footer
    send_telegram_message(current_chunk)

def fetch_naver_cafe_items(context, cafe_info):
    items = []
    page = None
    try:
        page = context.new_page()
        page.goto(cafe_info['url'], wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000) # 카페 UI 대기
        
        seen = set()
        # 메인 페이지 및 프레임에서 게시글 제목 추출
        elements = page.query_selector_all("a.article, a.article_item, .article-atcl, .article_title, .board_box a")
        
        for el in elements:
            try:
                title = clean_text(el.inner_text())
                if 4 <= len(title) <= 150 and title not in seen:
                    seen.add(title)
                    items.append(title)
            except Exception:
                continue
                
        # iframe(cafe_main) 내부 검사
        for frame in page.frames:
            if frame != page:
                frame_elements = frame.query_selector_all("a.article, a.article_item, .article-atcl, td.td_article a")
                for el in frame_elements:
                    try:
                        title = clean_text(el.inner_text())
                        if 4 <= len(title) <= 150 and title not in seen:
                            seen.add(title)
                            items.append(title)
                    except Exception:
                        continue
                        
        return items
    except Exception as e:
        print(f"   ❌ 네이버 카페 접속 패스: {str(e)[:60]}...")
        return []
    finally:
        if page:
            page.close()

# ============================================
# 메인 실행부
# ============================================

def main():
    print(f"☕ 네이버 카페 키워드 모니터링 시작: {get_kst_now().strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    
    history = load_history()
    found_new = False
    messages = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        
        for idx, cafe in enumerate(NAVER_CAFES, 1):
            cafe_name = cafe['name']
            cafe_url = cafe['url']
            target_keywords = cafe['keywords']
            print(f"[{idx}/{len(NAVER_CAFES)}] 🔍 모니터링 중: {cafe_name}")
            
            titles = fetch_naver_cafe_items(context, cafe)
            for title in titles:
                # 게시판별 지정된 키워드 포함 여부 검사
                if any(kw in title for kw in target_keywords):
                    history_key = f"{cafe_name}_{title}"
                    if history_key not in history:
                        print(f"   ✨ [신규 발견] {title}")
                        history[history_key] = get_kst_now().isoformat()
                        found_new = True
                        
                        messages.append(f"☕ <b>{cafe_name}</b>\n{title}\n🔗 {cafe_url}\n\n")

        browser.close()

    if found_new and messages:
        send_safe_telegram_messages(messages)
    else:
        print("\n✅ 조건에 맞는 신규 카페 글이 없습니다.")
        send_telegram_message(f"✅ 카페 확인 완료 (신규 글 없음) - {get_kst_now().strftime('%H:%M')} (KST)")
    
    save_history(history)
    print(f"\n✅ 카페 모니터링 프로세스 완료")

if __name__ == "__main__":
    main()
