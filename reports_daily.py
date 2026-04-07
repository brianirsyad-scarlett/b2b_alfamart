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

# ========== CATEGORY SELECTION ==========
# Set True to download, False to skip. Use the numeric values from the website.
CATEGORIES_TO_DOWNLOAD = {
    "3222": True,   # BEAUTY LIQUID SOAP
    "3251": True,   # BODY LOTION
    "3253": True,   # BODY SCRUB
    "3252": True,   # BODY SERUM
    "3246": True,   # FACE MASK
    "3243": True,   # FACIAL CLEANSER TONIC
    "3241": True,   # FACIAL WASH SOAP
    "3245": True,   # MOISTURIZER
    "8012": True,   # PROMOTION GOODS MEMBER
    "3249": True,   # SERUM ESSENCE
    "3240": True,   # SUNSCREEN
    "3232": True,   # WOMEN PARFUME & EDT
}
# ========================================

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

    set_select_value("indicator-filter-report-modular-3", "a")   # Selling Out
    set_select_value("tipe-area-filter-report-modular-3", "DC")
    set_select_value("branch-filter-report-modular-3", "NAS")
    set_select_value("store-filter-report-modular-3", "ALL")
    set_select_value("item-filter-report-modular-3", "ALL")
    close_sidebar()

    # Get selected categories (only those set to True)
    selected = [cat for cat, enabled in CATEGORIES_TO_DOWNLOAD.items() if enabled]
    if not selected:
        print("No categories selected.")
        return 0, 0

    print(f"Selected categories: {selected}")
    success = 0
    total = 0

    for cat_val in selected:
        # Get category name for display (optional)
        cat_name = next((name for name, val in {
            "3222": "BEAUTY LIQUID SOAP", "3251": "BODY LOTION", "3253": "BODY SCRUB",
            "3252": "BODY SERUM", "3246": "FACE MASK", "3243": "FACIAL CLEANSER TONIC",
            "3241": "FACIAL WASH SOAP", "3245": "MOISTURIZER", "8012": "PROMOTION GOODS MEMBER",
            "3249": "SERUM ESSENCE", "3240": "SUNSCREEN", "3232": "WOMEN PARFUME & EDT"
        }.items() if val == cat_val), cat_val)
        print(f"\nCategory: {cat_name}")
        set_select_value("category-filter-report-modular-3", cat_val)
        time.sleep(1)

        # Qty
        total += 1
        set_select_value("unit-filter-report-modular-3", "q")
        click_download()
        if handle_alert():
            print(f"❌ Qty failed for {cat_name}")
        else:
            success += 1
            print(f"✅ Qty succeeded")

        # Value
        total += 1
        handle_alert()
        set_select_value("unit-filter-report-modular-3", "v")
        click_download()
        if handle_alert():
            print(f"❌ Value failed for {cat_name}")
        else:
            success += 1
            print(f"✅ Value succeeded")

        time.sleep(2)
    return success, total

def date_range(start, end):
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    while s <= e:
        yield s.strftime("%Y-%m-%d")
        s += timedelta(days=1)

# --- Main execution ---
download_dir = "/tmp/downloads"
os.makedirs(download_dir, exist_ok=True)

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
prefs = {"download.default_directory": download_dir}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
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
        code = get_totp_code()
        print(f"Using TOTP code: {code}")
        code_field.send_keys(code)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']").click()
        time.sleep(3)
    except TimeoutException:
        print("No 2FA required.")

    close_popup()

    # Navigate to report
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

    # Loop over days
    total_s, total_t = 0, 0
    for day in date_range(START_DATE, END_DATE):
        s, t = process_day(day)
        total_s += s
        total_t += t
        time.sleep(3)

    print(f"\nDaily summary: {total_s}/{total_t} downloads succeeded.")
    print("Downloaded files:", os.listdir(download_dir))

except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
    driver.save_screenshot("error.png")
finally:
    driver.quit()
