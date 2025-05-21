import time
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Load environment variables
load_dotenv()

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
RECIPIENT_EMAIL_2 = os.getenv('RECIPIENT_EMAIL_2')

def setup_driver():
    """Setup and return Chrome driver"""
    options = uc.ChromeOptions()
    # options.add_argument('--headless')  # 주석 처리하여 브라우저 창이 보이도록 함
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')  # 브라우저 창을 최대화
    
    try:
        driver = uc.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"Error initializing Chrome driver: {e}")
        raise Exception("Failed to initialize Chrome driver. Please make sure Chrome is installed.")

def login(driver):
    """Handle login form"""
    try:
        # Wait for the form to be present
        wait = WebDriverWait(driver, 10)
        
        # Click the authentication tab first
        auth_tab = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href="/mjff/html/09/01.php"]')))
        auth_tab.click()
        
        # Wait for the form to be present after clicking the tab
        time.sleep(1)
        
        # Input name
        name_input = wait.until(EC.presence_of_element_located((By.NAME, 'u_name')))
        name_input.send_keys('강은지')
        
        # Input phone number
        phone_input = driver.find_element(By.NAME, 'u_hp')
        phone_input.send_keys('01090234505')
        
        # Input birth date
        birth_input = driver.find_element(By.NAME, 'u_pass')
        birth_input.send_keys('951109')
        
        # Find and click the submit button
        submit_button = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
        submit_button.click()
        
        # Wait for the page to load after submission
        time.sleep(2)
        
        return True
    except Exception as e:
        print(f"Error during login: {e}")
        return False

def send_email_notification(subject, message):
    """Send email notification to multiple recipients"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        # 여러 수신자를 리스트로 설정
        recipients = [RECIPIENT_EMAIL]
        if RECIPIENT_EMAIL_2:  # 두 번째 수신자가 설정되어 있으면 추가
            recipients.append(RECIPIENT_EMAIL_2)
        msg['To'] = ', '.join(recipients)  # 수신자들을 쉼표로 구분
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_error_notification(error_message):
    """Send error notification to primary recipient only"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL  # Only send to primary recipient
        msg['Subject'] = "⚠️ 무주등나무운동장 티켓 모니터링 오류 발생"

        message = f"""
        안녕하세요!
        
        무주등나무운동장 티켓 모니터링 중 오류가 발생했습니다.
        
        오류 내용:
        {error_message}
        
        프로그램을 확인해주세요.
        
        이 메일은 자동으로 발송되었습니다.
        """
        
        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending error notification: {e}")
        return False

def check_session(driver):
    """Check if the current session is valid"""
    try:
        # 현재 URL이 로그인 페이지인지 확인
        if "예매자 정보 인증" in driver.page_source:
            return False
        return True
    except Exception as e:
        print(f"Error checking session: {e}")
        return False

def check_ticket_availability(driver):
    """Check if any ticket is available using Selenium"""
    url = "https://www.dtidea.kr/mjff/html/03/01.php?idx=7"
    
    try:
        print("Checking ticket availability...")
        
        # 세션 체크
        if not check_session(driver):
            print("Session invalid, attempting to login...")
            login_url = "https://www.dtidea.kr/mjff/html/09/02.php"
            driver.get(login_url)
            if not login(driver):
                error_msg = "세션 만료 후 재로그인 실패"
                print(error_msg)
                send_error_notification(error_msg)
                return False, []
            time.sleep(2)
        
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(3)
        
        # Wait for the table to be present
        wait = WebDriverWait(driver, 10)
        try:
            table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'table_02')))
            print("Found ticket table")
        except Exception as e:
            print(f"Could not find ticket table: {e}")
            return False, []
            
        # Get all cells in the first row
        try:
            cells = table.find_elements(By.CSS_SELECTOR, 'td.taC')
            print(f"Found {len(cells)} cells")
            
            # Check only first two cells
            available_dates = []
            for i in range(2):  # Only check first two cells
                if i < len(cells):
                    cell = cells[i]
                    cell_text = cell.text.strip()
                    print(f"Cell {i+1} text: {cell_text}")
                    
                    # Check if the cell contains a link (GO.svg image)
                    has_link = len(cell.find_elements(By.TAG_NAME, 'a')) > 0
                    
                    if '매진' not in cell_text or has_link:
                        # Get the date from the header
                        date_header = table.find_elements(By.TAG_NAME, 'th')[i].text
                        available_dates.append(date_header)
            
            if available_dates:
                print(f"Tickets available for dates: {', '.join(available_dates)}")
                return True, available_dates
            else:
                print("All tickets are sold out")
                
        except Exception as e:
            print(f"Error checking cells: {e}")
            
        return False, []
        
    except Exception as e:
        print(f"Error checking ticket availability: {e}")
        return False, []

def main():
    print("Starting ticket monitoring...")
    
    try:
        driver = setup_driver()
        
        # 먼저 로그인 페이지로 이동
        login_url = "https://www.dtidea.kr/mjff/html/09/02.php"
        driver.get(login_url)
        
        # 로그인 수행
        if login(driver):
            print("Login successful!")
        else:
            error_msg = "로그인에 실패했습니다."
            print(error_msg)
            send_error_notification(error_msg)
            return
            
        # 티켓 모니터링 시작
        while True:
            try:
                is_available, available_dates = check_ticket_availability(driver)
                if is_available:
                    subject = "🎫 무주등나무운동장 티켓 예매 가능 알림"
                    message = f"""
                    안녕하세요!
                    
                    무주등나무운동장 티켓이 매진되지 않았습니다!
                    예매 가능한 날짜: {', '.join(available_dates)}
                    
                    지금 바로 예매하세요!
                    예매 링크: https://www.dtidea.kr/mjff/html/03/01.php?idx=7
                    
                    이 메일은 자동으로 발송되었습니다.
                    """
                    
                    if send_email_notification(subject, message):
                        print("Email notification sent successfully!")
                    else:
                        print("Failed to send email notification")
            except Exception as e:
                error_msg = f"티켓 확인 중 오류 발생: {str(e)}"
                print(error_msg)
                send_error_notification(error_msg)
            
            # Check every 1 minute
            print("Waiting 1 minute before next check...")
            time.sleep(60)
            
    except Exception as e:
        error_msg = f"프로그램 실행 중 오류 발생: {str(e)}"
        print(error_msg)
        send_error_notification(error_msg)
    except KeyboardInterrupt:
        print("\nStopping ticket monitoring...")
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    main() 