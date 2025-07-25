from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file
profile_path = os.getenv("PROFILE_PATH","")

options = Options()
options.set_preference("profile", profile_path)

service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=service, options=options)

driver.get("http://www.python.org")
assert "Python" in driver.title
elem = driver.find_element(By.NAME, "q")
elem.clear()
elem.send_keys("pycon")
elem.send_keys(Keys.RETURN)
assert "No results found." not in driver.page_source
# driver.close()
while True:
    pass  # Keep the browser open for manual inspection