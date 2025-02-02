import time
import random
import sqlite3
import xgboost as xgb
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Dynamic User-Agent list to randomize requests
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Mobile/15E148 Safari/604.1"
]

# Load the model from JSON
model = xgb.Booster()
model.load_model('xgboost_model.json')

# Database setup
def setup_database():
    conn = sqlite3.connect('profiles.db')  # Create or connect to database
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            followers_count INTEGER,
            following_count INTEGER,
            subscriptions_count INTEGER,
            is_verified BOOLEAN,
            status TEXT
        )
    ''')
    conn.commit()
    return conn

# Insert profile data into the database
def insert_profile_data(conn, profile_data):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO profiles (username, followers_count, following_count, subscriptions_count, is_verified, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (profile_data['username'], profile_data['followers_count'], profile_data['following_count'], 
          profile_data['subscriptions_count'], profile_data['is_verified'], profile_data['status']))
    conn.commit()

# Dynamic wait function with retries
def find_element(driver, by, value, timeout=10):
    attempts = 0
    while attempts < 2:  # Retry twice
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Attempt {attempts + 1}: Error finding element {value}: {e}")
            attempts += 1
            time.sleep(2)  # Retry after waiting
    return None  # Return None if all retries fail

# Close pop-up with dynamic XPath and force click
def close_pop_up(driver):
    close_button_xpath = "//*[@id='layers']//button"
    close_button = find_element(driver, By.XPATH, close_button_xpath)
    
    if close_button:
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", close_button)
            time.sleep(1)
            close_button.click()
            print("Pop-up closed.")
        except Exception as e:
            print(f"Element click intercepted, forcing click with JavaScript: {e}")
            driver.execute_script("arguments[0].click();", close_button)
    else:
        print("No close button found. Skipping pop-up closing.")

def parse_count(count_string):
    try:
        count_string = count_string.strip()

        if 'M' in count_string:
            return int(float(count_string.replace('M', '').split('.')[0])) * 1_000_000
        
        elif ',' in count_string:
            return int(float(count_string.replace(',', '')))

        elif 'K' in count_string:
            return int(float(count_string.replace('K', '').split('.')[0])) * 1_000

        else:
            return int(float(count_string.split('.')[0]))
    
    except ValueError:
        return 0 

def analyze_profile_data(profile_data):
    # Prepare input features for the model
    features = [[
        profile_data['followers_count'],
        profile_data['following_count'],
        profile_data['subscriptions_count'],
        int(profile_data['is_verified'])  # Convert boolean to int
    ]]
    
    # Convert features to DMatrix
    dmatrix = xgb.DMatrix(features)
    
    # Predict using the loaded model
    prediction = model.predict(dmatrix)
    
    # Interpret the prediction
    if prediction[0] > 0.5:  # Assuming 1 is 'genuine' and 0 is 'fake'
        return "Genuine"
    else:
        return "Fake"

def extract_profile_data(driver, username):
    try:
        driver.get(f"https://x.com/{username}/")
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )  # Wait for page load

        close_pop_up(driver)
        time.sleep(2)

        user_header_xpath = "//div[contains(@data-testid, 'UserName')]"
        user_header = find_element(driver, By.XPATH, user_header_xpath)

        if not user_header:
            print(f"User header not found for {username}.")
            return None

        followers_count_xpath_1 = "//a[contains(@href,'followers')]//span[1]"
        followers_count_xpath_2 = "//a[contains(@href,'followers')]//span[1]/span"  # Fallback XPath
        followers_count_elem = find_element(driver, By.XPATH, followers_count_xpath_1)
        if not followers_count_elem:  # If the first XPath fails, try the second one
            print(f"Fallback to secondary XPath for followers count for {username}.")
            followers_count_elem = find_element(driver, By.XPATH, followers_count_xpath_2)

        followers_count = parse_count(followers_count_elem.text) if followers_count_elem else 0

        following_count_xpath_1 = "//a[contains(@href,'following')]//span[1]"
        following_count_xpath_2 = "//a[contains(@href,'following')]//span[contains(@class, 'r-')][1]//span"  # Fallback XPath

        following_count_elem = find_element(driver, By.XPATH, following_count_xpath_1)
        if not following_count_elem:  # If the first XPath fails, try the second one
            print(f"Fallback to secondary XPath for following count for {username}.")
            following_count_elem = find_element(driver, By.XPATH, following_count_xpath_2)

        following_count = parse_count(following_count_elem.text) if following_count_elem else 0

        subscriptions_count_xpath = "//a[contains(@href,'subscriptions')]//span"
        subscriptions_count_elem = find_element(driver, By.XPATH, subscriptions_count_xpath)
        subscriptions_count = parse_count(subscriptions_count_elem.text) if subscriptions_count_elem else 0

        is_verified = bool(find_element(driver, By.XPATH, "//div[@id='react-root']//main//div[contains(@class, 'css-175oi2r')]//span[contains(@class, 'r-')]//div[1]"))

        profile_data = {
            'username': username,
            'followers_count': followers_count,
            'following_count': following_count,
            'subscriptions_count': subscriptions_count,
            'is_verified': is_verified
        }

        profile_data['status'] = analyze_profile_data(profile_data)  # Analyze using the loaded model
        return profile_data

    except Exception as e:
        print(f"Error extracting profile data for {username}: {e}")
        return None

def monitor_profiles(profiles):
    results = []
    
    options = Options()
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    # Setup database connection
    conn = setup_database()

    for username in profiles:
        print(f"Monitoring Twitter profile: {username}...")
        profile_data = extract_profile_data(driver, username)
        
        if profile_data:
            insert_profile_data(conn, profile_data)  # Insert profile data into the database
            results.append(profile_data)
            print(f"Profile data for {username}: {profile_data}")
        else:
            print(f"Failed to extract data for {username}.")
        
        time.sleep(random.uniform(5, 10))  # Random sleep to avoid detection
    
    driver.quit()  # Close the browser after all profiles
    conn.close()  # Close database connection
    return results

profiles_to_monitor = ['iamsrk']  # Replace with actual usernames

df_results = monitor_profiles(profiles_to_monitor)
print(df_results)
