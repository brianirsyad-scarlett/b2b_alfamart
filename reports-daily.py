import time
import os
import traceback
from datetime import datetime, timedelta
import pyotp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ========== CONFIGURATION ==========
USERNAME = "O-0108_10"
PASSWORD = "Scarlett2024!"
START_DATE = "2026-04-01"   # YYYY-MM-DD
END_DATE   = "2026-04-05"   # YYYY-MM-DD
# ===================================

TOTP_SECRET = os.environ.get("TOTP_SECRET")
if not TOTP_SECRET:
    raise ValueError("Missing TOTP_SECRET environment variable")

def get_totp_code():
    return pyotp.TOTP(TOTP_SECRET).now()

def wait_for_form():
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, "frm-filter-report-modular-4"))
    )
    print("Form ready.")
    time.sleep(1)

def set_select_value(select_id, value):
    select = driver.find_element(By.ID, select_id)
    driver.execute_script("arguments[0].value = arguments[1];", select, value)
    driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", select)
    print(f"Set {select_id} = {value}")

def set_single_day(target_day):
    target_date = datetime.strptime(target_day, "%Y-%m-%d")
    today = datetime.now()
    max_allowed = today - timedelta(days=2)
    if target_date > max_allowed:
        print(f"Skipping {target_day} (future).")
        return False
    start_input = driver.find_element(By.ID, "periode_awal")
    end_input = driver.find_element(By.ID, "periode_akhir")
    driver.execute_script("arguments[0].value = arguments[1];", start_input, target_day)
    driver.execute_script("arguments[0].value = arguments[1];", end_input, target_day)
    print(f"Date = {target_day}")
    return True

def click_download():
    btn = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "download-xls")))
    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", btn)
    print("Download clicked.")
    time.sleep(2)

def handle_alert():
    try:
        alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
        text = alert.text
        alert.accept()
        print(f"Alert: {text}")
        return text
    except TimeoutException:
        return None

def close_sidebar():
    try:
        driver.find_element(By.CSS_SELECTOR, ".nav-toggler, .navbar-toggler").click()
        time.sleep(1)
    except:
        pass

def get_categories():
    select = driver.find_element(By.ID, "category-filter-report-modular-3")
    opts = select.find_elements(By.TAG_NAME, "option")
    return [opt.get_attribute("value") for opt in opts if opt.get_attribute("value") and opt.get_attribute("value") != "ALL"]

def close_popup():
    try:
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.close-btn"))).click()
        time.sleep(1)
    except:
        driver.execute_script("document.querySelectorAll('.modal, .popup').forEach(m => m.style.display='none');")

def process_day(day_str):
    print(f"\n--- Day: {day_str} ---")
    if not set_single_day(day_str):
        return 0, 0
    set_select_value("indicator-filter-report-modular-3", "a")
    set_select_value("tipe-area-filter-report-modular-3", "DC")
    set_select_value("branch-filter-report-modular-3", "NAS")
    set_select_value("store-filter-report-modular-3", "ALL")
    set_select_value("item-filter-report-modular-3", "ALL")
    close_sidebar()
    categories = get_categories()
    if not categories:
        print("No categories.")
        return 0, 0
    success = 0
    total = 0
    for cat in categories:
        print(f"\nCategory: {cat}")
        set_select_value("category-filter-report-modular-3", cat)
        time.sleep(1)
        # Qty
        total += 1
        set_select_value("unit-filter-report-modular-3", "q")
        click_download()
        if handle_alert():
            print(f"❌ Qty failed for {cat}")
        else:
            success += 1
            print(f"✅ Qty ok")
        # Value
        total += 1
        handle_alert()
        set_select_value("unit-filter-report-modular-3", "v")
        click_download()
        if handle_alert():
            print(f"❌ Value failed for {cat}")
        else:
            success += 1
            print(f"✅ Value ok")
        time.sleep(2)
    return success, total

def date_range(start, end):
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    while s <= e:
        yield s.strftime("%Y-%m-%d")
        s += timedelta(days=1)

# --- Main ---
download_dir = "/tmp/downloads"
os.makedirs(download_dir, exist_ok=True)
opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")
opts.add_experimental_option("prefs", {"download.default_directory": download_dir})
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
driver.implicitly_wait(5)

try:
    # Login
    driver.get("https://b2b.alfamart.co.id/login.php")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "uname"))).send_keys(USERNAME)
    driver.find_element(By.ID, "upass").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "input.btn[value='Login']").click()
    time.sleep(3)
    # 2FA
    try:
        code_field = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "code")))
        code_field.send_keys(get_totp_code())
        driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']").click()
        time.sleep(3)
    except TimeoutException:
        print("No 2FA")
    close_popup()
    # Navigate
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul#nav")))
    laporan = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[@class='dir' and text()='Laporan']")))
    ActionChains(driver).move_to_element(laporan).perform()
    time.sleep(1)
    dashboard = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Dashboard & Modular')]")))
    dashboard.click()
    time.sleep(2)
    for handle in driver.window_handles:
        if handle != driver.current_window_handle:
            driver.switch_to.window(handle)
            break
    modular = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Report Modular')]")))
    modular.click()
    time.sleep(3)
    # Select report type
    perf = driver.find_element(By.ID, "jenis_performace")
    perf.click()
    perf.find_element(By.XPATH, "//option[@value='4']").click()
    time.sleep(2)
    wait_for_form()
    # Loop days
    total_s, total_t = 0, 0
    for day in date_range(START_DATE, END_DATE):
        s, t = process_day(day)
        total_s += s
        total_t += t
        time.sleep(3)
    print(f"\nDaily summary: {total_s}/{total_t} downloads succeeded.")
    print("Files in", download_dir, os.listdir(download_dir))
except Exception as e:
    print(e)
    traceback.print_exc()
    driver.save_screenshot("error.png")
finally:
    driver.quit()
