import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from slack_sdk import WebClient

load_dotenv()

URL = 'https://b7id.cz/marketplace?raceId=699b407072bb7f5cd634f41a'
USERNAME_SELECTOR = "input#\:r5\:"
PASSWORD_SELECTOR = "input#\:r6\:"
LOGIN_BUTTON_SELECTOR = "button.MuiButtonBase-root:nth-child(4)"
MARKETPLACE_BUTTON_SELECTOR = "a.MuiButton-root:nth-child(2)"
EMPTY_STATE_SELECTOR = "div.css-cp0569 p.css-t2rycj"


def login(driver):
    element = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, USERNAME_SELECTOR))
    )
    username = driver.find_element(By.CSS_SELECTOR, USERNAME_SELECTOR)
    password = driver.find_element(By.CSS_SELECTOR, PASSWORD_SELECTOR)

    username.send_keys(os.getenv("B7_LOGIN"))
    password.send_keys(os.getenv("B7_PASSWORD"))
    driver.find_element(By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR).click()
    

def enter_marketplace(driver):
    marketplace_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, MARKETPLACE_BUTTON_SELECTOR))
    )
    marketplace_button.click()

def check_for_listings(driver):
    try:
        listings = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, EMPTY_STATE_SELECTOR))
        )
        return False, None
    except NoSuchElementException:
        body = driver.find_element(By.TAG_NAME, "body").text
        return True, body
    
def send_alert(message):
    slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    slack_client.chat_postMessage(channel=os.getenv("ALERTS_CHANNEL_ID"), text=message)
    
def run():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome()
    driver.get(URL)

    try:
        print("Logging in...")
        login(driver)
        print("Logged in. Entering marketplace...")
        enter_marketplace(driver)
        print("Checking for listings...")
        has_listings, page_text = check_for_listings(driver)
        if has_listings:
            print("Listings found! Sending notification...")
            send_alert("New listings found! {url}".format(url=URL))
        else:
            print(f"No listings yet.")
            send_alert("Sadly, nothing new.")
    finally:
        driver.quit()


if __name__=='__main__':
    run()
