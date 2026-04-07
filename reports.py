import time
import os
import traceback
from datetime import datetime, timedelta
import calendar
import pyotp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ========== CONFIGURATION ==========
USERNAME = "O-0108_10"
PASSWORD = "Scarlett2024!"
START_DATE = "2026-04-01"   # YYYY-MM-DD
END_DATE   = "2026-04-30"   # YYYY-MM-DD
# ===================================

# Get TOTP secret from environment (set by GitHub Actions)
TOTP_SECRET = os.environ.get("TOTP_SECRET")
if not TOTP_SECRET:
    raise ValueError("Missing TOTP_SECRET environment variable")

def get_totp_code():
    totp = pyotp.TOTP(TOTP_SECRET)
    return totp.now()

def wait_for_form():
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "frm-filter-report-modular-4"))
        )
        print("Form frm-filter-report-modular-4 is present.")
        time.sleep(1)
    except TimeoutException:
        print("Form not found within timeout.")
        raise

def set_select_value(select_id, value):
    try:
        select = driver.find_element(By.ID, select_id)
        driver.execute_script("arguments[0].value = arguments[1];", select, value)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", select)
        print(f"Select {select_id} set to {value}")
    except Exception as e:
        print(f"Error setting select {select_id}: {e}")
        raise

def set_single_day(target_day):
    """
    Set both start and end date inputs to the same target_day (YYYY-MM-DD).
    Respects the max allowed date (today - 2 days).
    Returns True if date is valid, False if skipped (future date).
    """
    target_date = datetime.strptime(target_day, "%Y-%m-%d")
    today = datetime.now()
    max_allowed = today - timedelta(days=2)

    if target_date > max_allowed:
        print(f"⚠️ Skipping {target_day}: date is after {max_allowed.strftime('%Y-%m-%d')} (today - 2 days).")
        return False

    start_input = driver.find_element(By.ID, "periode_awal")
    end_input = driver.find_element(By.ID, "periode_akhir")
    driver.execute_script("arguments[0].value = arguments[1];", start_input, target_day)
    driver.execute_script("arguments[0].value = arguments[1];", end_input, target_day)
    print(f"Date set to: {target_day}")
    return True

def click_download():
    download_btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "download-xls"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", download_btn)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", download_btn)
    print("Download clicked (JavaScript).")
    time.sleep(2)

def handle_alert():
    try:
        alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert_text = alert.text
        alert.accept()
        print(f"Alert accepted: {alert_text}")
        return alert_text
    except TimeoutException:
        return None

def close_sidebar_if_needed():
    try:
        toggle = driver.find_element(By.CSS_SELECTOR, ".nav-toggler, .navbar-toggler")
        toggle.click()
        print("Sidebar toggled closed.")
        time.sleep(1)
    except:
        pass

def get_categories():
    cat_select = driver.find_element(By.ID, "category-filter-report-modular-3")
    options = cat_select.find_elements(By.TAG_NAME, "option")
    categories = []
    for opt in options:
        val = opt.get_attribute("value")
        if val and val != "ALL":
            categories.append(val)
    return categories

def close_popup():
    try:
        close_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "span.close-btn"))
        )
        close_btn.click()
        print("Popup closed by clicking close button.")
        time.sleep(1)
        return True
    except TimeoutException:
        print("No popup found or close button not clickable.")
        return False
    except Exception as e:
        print(f"Error closing popup: {e}")
        try:
            driver.execute_script("""
                var modals = document.querySelectorAll('.modal, .popup, .overlay');
                modals.forEach(m => m.style.display = 'none');
            """)
            print("Popup hidden via JavaScript.")
            return True
        except:
            return False

def process_day(day_str):
    print(f"\n{'='*50}")
    print(f"Processing day: {day_str}")
    print('='*50)

    if not set_single_day(day_str):
        return 0, 0

    set_select_value("indicator-filter-report-modular-3", "a")
    set_select_value("tipe-area-filter-report-modular-3", "DC")
    set_select_value("branch-filter-report-modular-3", "NAS")
    set_select_value("store-filter-report-modular-3", "ALL")
    set_select_value("item-filter-report-modular-3", "ALL")

    close_sidebar_if_needed()

    categories = get_categories()
    if not categories:
        print("No categories found. Skipping day.")
        return 0, 0

    print(f"Found {len(categories)} categories.\n")

    success = 0
    total = 0

    for cat_val in categories:
        print(f"\n--- Processing category: {cat_val} ---")
        set_select_value("category-filter-report-modular-3", cat_val)
        time.sleep(1)

        # Qty
        total += 1
        set_select_value("unit-filter-report-modular-3", "q")
        click_download()
        alert_text = handle_alert()
        if alert_text and "gagal" in alert_text.lower():
            print(f"❌ Download failed for {cat_val}, Qty: {alert_text}")
        else:
            print(f"✅ Download succeeded for {cat_val}, Qty")
            success += 1

        # Value
        total += 1
        handle_alert()
        set_select_value("unit-filter-report-modular-3", "v")
        click_download()
        alert_text = handle_alert()
        if alert_text and "gagal" in alert_text.lower():
            print(f"❌ Download failed for {cat_val}, Value: {alert_text}")
        else:
            print(f"✅ Download succeeded for {cat_val}, Value")
            success += 1

        time.sleep(2)

    print(f"\nDay {day_str} completed: {success} successful downloads out of {total}.")
    return success, total

def date_range(start_str, end_str):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    delta = timedelta(days=1)
    while start <= end:
        yield start.strftime("%Y-%m-%d")
        start += delta

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
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "ul#nav"))
    )
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
    print("Step 1: Selected 'Performance by Item by Store by Day'.")
    time.sleep(2)

    wait_for_form()

    # ---- LOOP OVER DAYS ----
    total_success = 0
    total_attempts = 0
    days = list(date_range(START_DATE, END_DATE))
    print(f"\nWill process {len(days)} days: {', '.join(days)}\n")

    for day_str in days:
        s, t = process_day(day_str)
        total_success += s
        total_attempts += t
        time.sleep(3)

    print(f"\n{'='*50}")
    print(f"FINAL SUMMARY")
    print(f"Total successful downloads: {total_success} out of {total_attempts}")
    if total_success == total_attempts:
        print("✅ All downloads succeeded! Reports should be sent to your email.")
    else:
        print("⚠️ Some downloads failed. Check the alerts above for details.")
    print('='*50)

    # List downloaded files (for debugging)
    print("\nDownloaded files in", download_dir)
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
