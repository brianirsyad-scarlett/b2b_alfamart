import time
import os
import traceback
from datetime import datetime
import calendar
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

# ========== CATEGORY SELECTION ==========
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

def set_month_range(year_month):
    year, month = map(int, year_month.split('-'))
    first_day = datetime(year, month, 1).strftime("%Y-%m-%d")
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).strftime("%Y-%m-%d")
    start_input = driver.find_element(By.ID, "periode_awal")
    end_input = driver.find_element(By.ID, "periode_akhir")
    driver.execute_script("arguments[0].value = arguments[1];", start_input, first_day)
    driver.execute_script("arguments[0].value = arguments[1];", end_input, last_day)
    print(f"Month range: {first_day} → {last_day}")
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

def process_month(year_month):
    """Process a single month (year_month = 'YYYY-MM') and return (success, total)."""
    print(f"\n{'='*50}")
    print(f"Processing month: {year_month}")
    print('='*50)

    set_month_range(year_month)
    set_select_value("indicator-filter-report-modular-3", "a")   # Selling Out
    set_select_value("tipe-area-filter-report-modular-3", "DC")
    set_select_value("branch-filter-report-modular-3", "NAS")
    set_select_value("store-filter-report-modular-3", "ALL")
    set_select_value("item-filter-report-modular-3", "ALL")
    close_sidebar()

    selected = [cat for cat, enabled in CATEGORIES_TO_DOWNLOAD.items() if enabled]
    if not selected:
        print("No categories selected.")
        return 0, 0

    print(f"Selected categories: {selected}")
    success = 0
    total = 0

    # Mapping from value to readable name
    cat_names = {
        "3222": "BEAUTY LIQUID SOAP", "3251": "BODY LOTION", "3253": "BODY SCRUB",
        "3252": "BODY SERUM", "3246": "FACE MASK", "3243": "FACIAL CLEANSER TONIC",
        "3241": "FACIAL WASH SOAP", "3245": "MOISTURIZER", "8012": "PROMOTION GOODS MEMBER",
        "3249": "SERUM ESSENCE", "3240": "SUNSCREEN", "3232": "WOMEN PARFUME & EDT"
    }

    for cat_val in selected:
        cat_name = cat_names.get(cat_val, cat_val)
        print(f"\n--- Category: {cat_name} (value={cat_val}) ---")
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
            print(f"✅ Qty succeeded for {cat_name}")

        # Value
        total += 1
        handle_alert()
        set_select_value("unit-filter-report-modular-3", "v")
        click_download()
        if handle_alert():
            print(f"❌ Value failed for {cat_name}")
        else:
            success += 1
            print(f"✅ Value succeeded for {cat_name}")

        time.sleep(2)

    print(f"\nMonth {year_month} completed: {success}/{total} downloads succeeded.")
    return success, total

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
    # ---- LOGIN ----
    driver.get("https://b2b.alfamart.co.id/login.php")
    print("Login page opened.")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "uname"))).send_keys(USERNAME)
    driver.find_element(By.ID, "upass").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "input.btn[value='Login']").click()
    print("Login button clicked.")
    time.sleep(3)

    # 2FA (automatic)
    try:
        code_field = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "code")))
        code = get_totp_code()
        print(f"Using TOTP code: {code}")
        code_field.send_keys(code)
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        submit_button.click()
        print("2FA submitted.")
        time.sleep(3)
    except TimeoutException:
        print("No 2FA required.")

    close_popup()

    # ---- WAIT FOR PAGE TO BE READY ----
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul#nav")))
    print("Page ready, top menu found.")

    # ---- NAVIGATION TO MODULAR REPORT ----
    laporan_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@class='dir' and text()='Laporan']"))
    )
    ActionChains(driver).move_to_element(laporan_link).perform()
    print("Hovered over 'Laporan'.")
    time.sleep(1)

    dashboard_link = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Dashboard & Modular')]"))
    )
    dashboard_link.click()
    print("Clicked Dashboard & Modular.")
    time.sleep(2)

    # Switch to new tab
    original_tab = driver.current_window_handle
    for tab in driver.window_handles:
        if tab != original_tab:
            driver.switch_to.window(tab)
            break
    print("Switched to new tab.")

    modular_button = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Report Modular')]"))
    )
    modular_button.click()
    print("Clicked Report Modular.")
    time.sleep(3)

    # ---- SETUP REPORT PAGE ----
    perf_dropdown = driver.find_element(By.ID, "jenis_performace")
    perf_dropdown.click()
    perf_dropdown.find_element(By.XPATH, "//option[@value='4']").click()
    print("Selected 'Performance by Item by Store by Day'.")
    time.sleep(2)

    wait_for_form()

    # ---- DETERMINE MONTHS (current and previous) ----
    today = datetime.now()
    current_month = today.strftime("%Y-%m")
    # Previous month: subtract one month, handle year wrap
    first_day_this_month = today.replace(day=1)
    previous_month_date = first_day_this_month - timedelta(days=1)
    previous_month = previous_month_date.strftime("%Y-%m")

    months_to_process = [current_month, previous_month]
    print(f"\nWill process months: {months_to_process}")

    total_success = 0
    total_attempts = 0

    for month in months_to_process:
        s, t = process_month(month)
        total_success += s
        total_attempts += t
        time.sleep(5)  # pause between months

    print(f"\n{'='*50}")
    print(f"FINAL SUMMARY (both months)")
    print(f"Total successful downloads: {total_success} out of {total_attempts}")
    if total_success == total_attempts:
        print("✅ All downloads succeeded!")
    else:
        print("⚠️ Some downloads failed. Check the alerts above for details.")
    print('='*50)

    print("Downloaded files in", download_dir)
    for f in os.listdir(download_dir):
        print(" -", f)

except Exception as e:
    print(f"An error occurred: {e}")
    traceback.print_exc()
    try:
        driver.save_screenshot("error_screenshot.png")
        print("Screenshot saved as error_screenshot.png")
    except:
        pass
finally:
    driver.quit()
