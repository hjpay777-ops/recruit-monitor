#!/usr/bin/env python3
"""
취업 공고 모니터링 봇 (Playwright 헤드리스 브라우저 - 단일 메세지 발송판)
- JavaScript Dynamic UI 지원 및 공공기관 방화벽/SSL 오류 완벽 대응
- 분할 발송 로직 제거: 신규 공고를 1개의 텔레그램 메세지로 일괄 전송
"""

import json
import os
import re
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

# ============================================
# 설정
# ============================================

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

SITES = [
    {"name": "남양주도시공사", "url": "https://www.ncuc.or.kr/main/261"},
    {"name": "남양주문화재단", "url": "https://www.nyjcf.or.kr/www/25"},
    {"name": "남양주복지재단", "url": "https://www.nyjwf.or.kr/Home/23?document_category_srl=20"},
    {"name": "남양주시정연구원", "url": "https://www.nyj.re.kr/Home/13"},
    {"name": "남양주자원봉사센터", "url": "https://www.nyjvc.or.kr/bbs?table=mn07_01"},
    {"name": "남양주장애인복지관", "url": "https://nyjwel.or.kr/bbs/board.php?bo_table=recruitment"},
    {"name": "남양주노인복지관", "url": "https://www.nyjsw.or.kr/main/sub.html?pageCode=31"},
    {"name": "남양주북부노인복지관", "url": "http://www.nyjbrc.com/bbs/board.php?bo_table=jobpost"},
    {"name": "남양주동부노인복지관", "url": "https://dongbusenior.or.kr/bbs/?bid=recruit"},
    {"name": "남양주다산노인복지관", "url": "https://dasanswc.or.kr/bbs/board.php?bo_table=recruit"},
    {"name": "남양주희망케어센터", "url": "https://hope.nyj.go.kr/www/74"},
    {"name": "구리도시공사", "url": "https://www.guriuc.or.kr/bbsArticle/list.do?bbsId=JOB_INFO"},
    {"name": "구리문화재단", "url": "https://www.guriart.or.kr/PageLink.do"},
    {"name": "구리문화원", "url": "https://gurimh.or.kr/bbs/board.php?bo_table=notice"},
    {"name": "구리농수산물공사", "url": "https://www.gamaco.co.kr/conIntroduction/employ/main"},
    {"name": "구리청소년재단", "url": "https://www.guriyouth.go.kr/www/178"},
    {"name": "구리상권활성화재단", "url": "https://www.gurimr.or.kr/board/notice.do"},
    {"name": "구리자원봉사센터", "url": "https://www.guri1365.or.kr/21"},
    {"name": "구리종합사회복지관", "url": "http://www.guriwelfare.or.kr/bbs/zboard.php?id=TemP_recruit"},
    {"name": "구리장애인종합복지관", "url": "https://guriwel.or.kr/bbs/?bid=recruit"},
    {"name": "구리노인복지관", "url": "https://www.guri.go.kr/senior/selectBbsNttList.do?bbsNo=82&key=926"},
    {"name": "포천도시공사", "url": "https://www.pcuc.kr/open_content/participation/recruit.jsp"},
    {"name": "포천문화재단", "url": "https://www.pcfac.or.kr/sub07/sub03.php"},
    {"name": "포천문화원", "url": "http://www.pcmh.or.kr/board2/index.html?d_name=002&menu=06"},
    {"name": "포천농업재단", "url": "https://www.pcaf.or.kr/sub03/sub04.php"},
    {"name": "포천청소년재단", "url": "https://www.poyouth.or.kr/home/kor/M141175147/board.do?"},
    {"name": "포천자원봉사센터", "url": "https://pcvc.kr/board/notice.asp"},
    {"name": "포천종합사회복지관", "url": "https://www.pobok.or.kr/"},
    {"name": "포천노인복지관", "url": "http://www.pcsc.kr/bbs/board.php?bo_table=employ"},
    {"name": "의정부도시공사", "url": "https://www.uiuc.or.kr/companyNotice/employmentPage/employment/list.do"},
    {"name": "의정부문화재단", "url": "https://www.uac.or.kr/newuac/community/community_09.php"},
    {"name": "의정부문화원", "url": "https://ujbcc.or.kr/bbs/board.php?bo_table=0301"},
    {"name": "의정부도시교육재단", "url": "https://www.uuli.or.kr/index.do?menu_id=00005064&servletPath=%2Findex.do"},
    {"name": "의정부장애인종합복지관", "url": "https://warmhand.or.kr/bbs/board.php?bo_table=0208"},
    {"name": "경기환경에너지진흥원", "url": "https://www.ggeea.or.kr/statute"},
    {"name": "경기문화재단", "url": "https://www.ggcf.kr/boards/bulletinBoards/articles?category=03"},
    {"name": "경기주택도시공사", "url": "https://www.gh.or.kr/gh/employment-announcement.do"},
    {"name": "경기복지재단", "url": "https://www.ggwf.or.kr/"},
    {"name": "서울의료원", "url": "https://smc.recruiter.co.kr/career/job(1)"},
    {"name": "경기공공보건의료지원단", "url": "https://ggpi.or.kr/board/notice_list.asp?cat=2&searchValue=&searchtxt="}
]

KEYWORDS = ["채용", "모집", "합격", "공모", "인재"]
HISTORY_FILE = "/tmp/recruit_history.json"

# ============================================
# 헬퍼 함수들
# ============================================

def clean_text(text):
    """불필요한 공백 및 줄바꿈 정리"""
    return re.sub(r'\s+', ' ', text).strip()

def load_history():
    """이전 모니터링 기록 불러오기"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    """최신 모니터링 기록 저장하기"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def send_telegram_message(message):
    """텔레그램 메시지 단일 발송"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)이 없습니다!")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 텔레그램 발송 오류: {str(e)}")
        return False

def fetch_titles_with_browser(context, url):
    """Playwright 크롬 브라우저로 접속하여 페이지 내 텍스트 추출"""
    titles = []
    page = None
    try:
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        
        elements = page.query_selector_all("a, td, div.title, h3, h4, span")
        seen = set()
        
        for el in elements:
            try:
                text = clean_text(el.inner_text())
                if 6 <= len(text) <= 120 and text not in seen:
                    if not any(bad in text for bad in ["원문보기", "다운로드", "더보기", "바로가기", "검색", "로그인", "사이트맵"]):
                        seen.add(text)
                        titles.append(text)
            except Exception:
                continue
                
        return titles
    except Exception as e:
        print(f"   ❌ 접속/파싱 실패: {str(e)}")
        return []
    finally:
        if page:
            page.close()

# ============================================
# 메인 실행부
# ============================================

def main():
    print(f"🤖 Playwright 기반 채용 공고 모니터링 시작: {datetime.now()}")
    print("=" * 50)
    
    history = load_history()
    found_new = False
    messages = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        
        for site in SITES:
            site_name = site['name']
            site_url = site['url']
            print(f"\n🔍 확인 중: {site_name} ({site_url})")
            
            titles = fetch_titles_with_browser(context, site_url)
            
            if not titles:
                print("   → 가져온 제목이 없거나 접속에 실패했습니다.")
                continue
                
            site_found_count = 0
            for title in titles:
                if any(kw in title for kw in KEYWORDS):
                    history_key = f"{site_name}_{title}"
                    if history_key not in history:
                        print(f"   ✨ 신규: {title}")
                        history[history_key] = datetime.now().isoformat()
                        found_new = True
                        messages.append(f"🎯 <b>{site_name}</b>\n{title}\n🔗 {site_url}\n")
                        site_found_count += 1
                        
            if site_found_count == 0:
                print("   → 신규 채용 관련 공고 없음")
                
        browser.close()

    # 텔레그램 메시지 단 1회 전송
    if found_new and messages:
        message_text = f"🚀 새로운 채용 공고가 올라왔습니다!\n\n"
        message_text += "\n".join(messages)
        message_text += f"\n⏰ 확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        send_telegram_message(message_text)
    else:
        print("\n✅ 새 공고 없음")
        send_telegram_message(f"✅ 확인됨 (새 공고 없음) - {datetime.now().strftime('%H:%M')}")
    
    save_history(history)
    print(f"\n✅ 모니터링 완료")

if __name__ == "__main__":
    main()
