#!/usr/bin/env python3
"""
취업 공고 모니터링 봇
GitHub Actions에서 자동 실행됨
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from urllib.parse import urljoin

# ============================================
# 설정 (나중에 GitHub Secrets에서 자동 가져옴)
# ============================================

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # GitHub Secrets에서 자동으로 받음
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # GitHub Secrets에서 자동으로 받음

# 모니터링할 사이트들
# 여기에 당신의 사이트 추가하세요!
SITES = [
    {
        "name": "남양주도시공사",
        "url": "https://www.ncuc.or.kr/main/261",
    },
    {
        "name": "남양주문화재단",
        "url": "https://www.nyjcf.or.kr/www/25",
    },
    {
        "name": "남양주복지재단",
        "url": "https://www.nyjwf.or.kr/Home/23?document_category_srl=20",
    },
    {
        "name": "남양주시정연구원",
        "url": "https://www.nyj.re.kr/Home/13",
    },
    {
        "name": "남양주자원봉사센터",
        "url": "https://www.nyjvc.or.kr/bbs?table=mn07_01",
    },
    {
        "name": "남양주장애인복지관",
        "url": "https://nyjwel.or.kr/bbs/board.php?bo_table=recruitment",
    },
    {
        "name": "남양주노인복지관",
        "url": "https://www.nyjsw.or.kr/main/sub.html?pageCode=31",
    },
    {
        "name": "남양주북부노인복지관",
        "url": "http://www.nyjbrc.com/bbs/board.php?bo_table=jobpost",
    },
    {
        "name": "남양주동부노인복지관",
        "url": "https://dongbusenior.or.kr/bbs/?bid=recruit",
    },
    {
        "name": "남양주다산노인복지관",
        "url": "https://dasanswc.or.kr/bbs/board.php?bo_table=recruit",
    },
    {
        "name": "남양주희망케어센터",
        "url": "https://hope.nyj.go.kr/www/74",
    },
    {
        "name": "구리도시공사",
        "url": "https://www.guriuc.or.kr/bbsArticle/list.do?bbsId=JOB_INFO",
    },
    {
        "name": "구리문화재단",
        "url": "https://www.guriart.or.kr/PageLink.do",
    },
    {
        "name": "구리문화원",
        "url": "https://gurimh.or.kr/bbs/board.php?bo_table=notice",
    },
    {
        "name": "구리농수산물공사",
        "url": "https://www.gamaco.co.kr/conIntroduction/employ/main",
    },
    {
        "name": "구리청소년재단",
        "url": "https://www.guriyouth.go.kr/www/178",
    },
    {
        "name": "구리상권활성화재단",
        "url": "https://www.gurimr.or.kr/board/notice.do",
    },
    {
        "name": "구리자원봉사센터",
        "url": "https://www.guri1365.or.kr/21",
    },
    {
        "name": "구리종합사회복지관",
        "url": "http://www.guriwelfare.or.kr/bbs/zboard.php?id=TemP_recruit",
    },
    {
        "name": "구리장애인종합복지관",
        "url": "https://guriwel.or.kr/bbs/?bid=recruit",
    },
    {
        "name": "구리노인복지관",
        "url": "https://www.guri.go.kr/senior/selectBbsNttList.do?bbsNo=82&key=926",
    },
    {
        "name": "포천도시공사",
        "url": "https://www.pcuc.kr/open_content/participation/recruit.jsp",
    },
    {
        "name": "포천문화재단",
        "url": "https://www.pcfac.or.kr/sub07/sub03.php",
    },
    {
        "name": "포천문화원",
        "url": "http://www.pcmh.or.kr/board2/index.html?d_name=002&menu=06",
    },
    {
        "name": "포천농업재단",
        "url": "https://www.pcaf.or.kr/sub03/sub04.php",
    },
    {
        "name": "포천청소년재단",
        "url": "https://www.poyouth.or.kr/home/kor/M141175147/board.do?",
    },
    {
        "name": "포천자원봉사센터",
        "url": "https://pcvc.kr/board/notice.asp",
    },
    {
        "name": "포천종합사회복지관",
        "url": "https://www.pobok.or.kr/",
    },
   {
        "name": "포천노인복지관",
        "url": "http://www.pcsc.kr/bbs/board.php?bo_table=employ",
    },
    {
        "name": "의정부도시공사",
        "url": "https://www.uiuc.or.kr/companyNotice/employmentPage/employment/list.do",
    },
    {
        "name": "의정부문화재단",
        "url": "https://www.uac.or.kr/newuac/community/community_09.php",
    },
    {
        "name": "의정부문화원",
        "url": "https://ujbcc.or.kr/bbs/board.php?bo_table=0301",
    },
    {
        "name": "의정부도시교육재단",
        "url": "https://www.uuli.or.kr/index.do?menu_id=00005064&servletPath=%2Findex.do",
    },
    {
        "name": "의정부장애인종합복지관",
        "url": "https://warmhand.or.kr/bbs/board.php?bo_table=0208",
    },
    {
        "name": "경기환경에너지진흥원",
        "url": "https://www.ggeea.or.kr/statute",
    },
    {
        "name": "경기문화재단",
        "url": "https://www.ggcf.kr/boards/bulletinBoards/articles?category=03",
    },
    {
        "name": "경기주택도시공사",
        "url": "https://www.gh.or.kr/gh/employment-announcement.do",
    },
    {
        "name": "경기복지재단",
        "url": "https://www.gh.or.kr/gh/employment-announcement.do",
    },
    {
        "name": "서울의료원",
        "url": "https://smc.recruiter.co.kr/career/job(1)",
    },
    {
        "name": "경기공공보건의료지원단",
        "url": "https://ggpi.or.kr/board/notice_list.asp?cat=2&searchValue=&searchtxt=",
    }
]

# 검색할 단어들
KEYWORDS = ["채용", "모집"]

# 이전 실행 데이터를 저장할 파일
HISTORY_FILE = "/tmp/recruit_history.json"

# ============================================
# 함수들
# ============================================

def load_history():
    """이전에 본 공고 불러오기"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_history(history):
    """새로 본 공고 저장하기"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def check_keywords(text):
    """텍스트에 채용 관련 단어 있는지 확인"""
    text_lower = text.lower()
    for keyword in KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    return False

def fetch_site_titles(url):
    """웹사이트에서 제목들 가져오기"""
    try:
        # 한국 사이트 대비
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, timeout=10, headers=headers)
        response.encoding = 'utf-8'  # 한글 인코딩
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 공통으로 사용되는 게시글 제목 태그들
        titles = []
        
        # h1, h2, h3 태그에서 찾기
        for tag in soup.find_all(['h1', 'h2', 'h3', 'a', 'td']):
            text = tag.get_text(strip=True)
            if text and len(text) > 5:  # 너무 짧은 건 제외
                titles.append(text[:100])  # 100자까지만
        
        return titles[:20]  # 상위 20개만
        
    except Exception as e:
        print(f"❌ {url} 접속 실패: {str(e)}")
        return []

def send_telegram_message(message):
    """텔레그램으로 메시지 보내기"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정이 없습니다!")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ 텔레그램 발송 성공")
            return True
        else:
            print(f"❌ 텔레그램 발송 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 텔레그램 오류: {str(e)}")
        return False

def main():
    """메인 함수"""
    print(f"🤖 채용 공고 모니터링 시작: {datetime.now()}")
    print("=" * 50)
    
    history = load_history()
    found_new = False
    messages = []
    
    # 각 사이트 확인
    for site in SITES:
        site_name = site['name']
        site_url = site['url']
        
        print(f"\n🔍 확인 중: {site_name} ({site_url})")
        
        titles = fetch_site_titles(site_url)
        
        if not titles:
            print(f"   → 제목을 가져올 수 없습니다")
            continue
        
        # 채용 관련 제목 찾기
        for title in titles:
            if check_keywords(title):
                # 이전에 본 것인지 확인
                if title not in history:
                    print(f"   ✨ 신규: {title}")
                    history[title] = datetime.now().isoformat()
                    found_new = True
                    messages.append(f"🎯 <b>{site_name}</b>\n{title}\n🔗 {site_url}\n")
    
    # 새 공고가 있으면 텔레그램 발송
    if found_new and messages:
        message_text = "🚀 새로운 채용 공고가 올라왔습니다!\n\n"
        message_text += "\n".join(messages)
        message_text += f"\n⏰ 확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        send_telegram_message(message_text)
    else:
        print("\n✅ 새 공고 없음")
        send_telegram_message(f"✅ 확인됨 (새 공고 없음) - {datetime.now().strftime('%H:%M')}")
    
    # 히스토리 저장
    save_history(history)
    print(f"\n✅ 모니터링 완료")

if __name__ == "__main__":
    main()
