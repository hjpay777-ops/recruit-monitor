#!/usr/bin/env python3
"""
취업 공고 모니터링 봇 (개선판)
- 공공기관 방화벽/SSL 차단 우회 강화
- 범용 텍스트 추출 로직으로 도시공사 및 문화재단 파싱율 극대화
"""

import json
import os
import re
import time
from datetime import datetime
import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# SSL 경고 메세지 무시 설정
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
# 함수들
# ============================================

def create_robust_session():
    """방화벽 및 네트워크 불안정성을 극복하기 위한 커스텀 세션 생성"""
    session = requests.Session()
    
    # 자동 재시도 설정 (3회 재시도, 지연 시간 포함)
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 실제 브라우저와 동일한 헤더 설정
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    return session

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def check_keywords(text):
    for keyword in KEYWORDS:
        if keyword in text:
            return True
    return False

def clean_text(text):
    """불필요한 공백 제거"""
    return re.sub(r'\s+', ' ', text).strip()

def fetch_site_titles(session, url):
    """모든 태그 탐색 방식으로 제목 추출 개선"""
    try:
        response = session.get(url, timeout=20, verify=False)
        response.encoding = response.apparent_encoding or 'utf-8'
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 스크립트 및 스타일 태그 제거
        for script in soup(["script", "style", "header", "footer", "nav"]):
            script.extract()
            
        titles = []
        seen = set()
        
        # 페이지 내 모든 태그의 텍스트 탐색
        for tag in soup.find_all(True):
            # 자식 태그가 너무 많으면 상위 컨테이너이므로 스킵
            if len(tag.find_all(True)) > 3:
                continue
                
            text = clean_text(tag.get_text())
            
            # 길이 조건 및 중복 체크 (글자수 6자 이상 ~ 120자 이하)
            if 6 <= len(text) <= 120 and text not in seen:
                # 메뉴명/버튼명 등 무의미한 단어 필터링
                if any(bad in text for bad in ["원문보기", "다운로드", "더보기", "바로가기", "검색"]):
                    continue
                seen.add(text)
                titles.append(text)
        
        return titles
        
    except Exception as e:
        print(f"❌ {url} 접속 실패: {str(e)}")
        return []

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정이 없습니다!")
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
        print(f"❌ 텔레그램 오류: {str(e)}")
        return False

def main():
    print(f"🤖 채용 공고 모니터링 시작: {datetime.now()}")
    print("=" * 50)
    
    session = create_robust_session()
    history = load_history()
    found_new = False
    messages = []
    
    for site in SITES:
        site_name = site['name']
        site_url = site['url']
        
        print(f"\n🔍 확인 중: {site_name} ({site_url})")
        
        titles = fetch_site_titles(session, site_url)
        
        if not titles:
            print(f"   → 제목을 가져올 수 없습니다")
            continue
            
        site_found_count = 0
        for title in titles:
            if check_keywords(title):
                history_key = f"{site_name}_{title}"
                if history_key not in history:
                    print(f"   ✨ 신규: {title}")
                    history[history_key] = datetime.now().isoformat()
                    found_new = True
                    messages.append(f"🎯 <b>{site_name}</b>\n{title}\n🔗 {site_url}\n")
                    site_found_count += 1
                    
        if site_found_count == 0:
            print("   → 검색된 채용 관련 공고 없음")

    # 텔레그램 메시지 분할 발송 (10개씩 전송)
    if found_new and messages:
        chunk_size = 10
        total_chunks = (len(messages) + chunk_size - 1) // chunk_size
        
        for idx, i in enumerate(range(0, len(messages), chunk_size)):
            chunk = messages[i:i + chunk_size]
            message_text = f"🚀 새로운 채용 공고가 올라왔습니다! ({idx + 1}/{total_chunks})\n\n"
            message_text += "\n".join(chunk)
            message_text += f"\n⏰ 확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            send_telegram_message(message_text)
            time.sleep(1)
    else:
        print("\n✅ 새 공고 없음")
        send_telegram_message(f"✅ 확인됨 (새 공고 없음) - {datetime.now().strftime('%H:%M')}")
    
    save_history(history)
    print(f"\n✅ 모니터링 완료")

if __name__ == "__main__":
    main()
