import os
import time
import logging
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from slack_sdk import WebClient

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

URL = 'https://b7id.cz/marketplace?raceId=699b407072bb7f5cd634f41a'
USERNAME_SELECTOR = "input#\\:r5\\:"
PASSWORD_SELECTOR = "input#\\:r6\\:"
LOGIN_BUTTON_SELECTOR = "button.MuiButtonBase-root:nth-child(4)"
MARKETPLACE_BUTTON_SELECTOR = "a.MuiButton-root:nth-child(2)"
EMPTY_STATE_SELECTOR = "div.css-cp0569 p.css-t2rycj"

CHECK_INTERVAL = 120  # seconds
MAX_RETRIES = 3


def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")  # important for NAS/low-memory envs
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(options=options)


def login(driver):
    driver.get(URL)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, USERNAME_SELECTOR))
    )
    driver.find_element(By.CSS_SELECTOR, USERNAME_SELECTOR).send_keys(os.getenv("B7_LOGIN"))
    driver.find_element(By.CSS_SELECTOR, PASSWORD_SELECTOR).send_keys(os.getenv("B7_PASSWORD"))
    driver.find_element(By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR).click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, MARKETPLACE_BUTTON_SELECTOR))
    )


def enter_marketplace(driver):
    driver.find_element(By.CSS_SELECTOR, MARKETPLACE_BUTTON_SELECTOR).click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, EMPTY_STATE_SELECTOR))
    )


def check_for_listings(driver):
    # Reload the page each check to get fresh content
    driver.get(URL)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, EMPTY_STATE_SELECTOR))
        )
        return False, None
    except TimeoutException:
        # Empty state didn't appear — listings are present
        body = driver.find_element(By.TAG_NAME, "body").text
        return True, body


def send_alert(message):
    slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    slack_client.chat_postMessage(
        channel=os.getenv("ALERTS_CHANNEL_ID"),
        text=message
    )


def run():
    driver = None
    retries = 0

    while True:
        try:
            if driver is None:
                logging.info("Starting browser and logging in...")
                driver = create_driver()
                login(driver)
                logging.info("Logged in successfully.")

            has_listings, page_text = check_for_listings(driver)

            if has_listings:
                logging.info("Listings found! Sending alert...")
                send_alert(f"🔔 New listings found! {URL}")
                # Keep monitoring — remove the break if you want repeated alerts
                # or add a cooldown to avoid spamming
            else:
                logging.info("No listings yet.")

            retries = 0  # reset retry counter on success
            time.sleep(CHECK_INTERVAL)

        except (TimeoutException, WebDriverException) as e:
            retries += 1
            logging.warning(f"Browser/session error (attempt {retries}/{MAX_RETRIES}): {e}")

            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None

            if retries >= MAX_RETRIES:
                logging.error("Max retries reached. Sending alert and pausing for 10 minutes.")
                try:
                    send_alert("⚠️ b7id scraper is having issues and needs attention.")
                except Exception:
                    pass
                retries = 0
                time.sleep(600)
            else:
                time.sleep(30)  # short wait before retrying

        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    run()