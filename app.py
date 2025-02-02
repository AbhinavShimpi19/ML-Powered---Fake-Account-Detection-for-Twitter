# backend/app.py

import os
import time
import random
import sqlite3
import xgboost as xgb
from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

app = Flask(__name__)

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
    conn = sqlite3.connect('profiles.db')
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
    while attempts < 2:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Attempt {attempts + 1}: Error finding element {value}: {e}")
            attempts += 1
            time.sleep(2)
    return None

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
    features = [[
        profile_data['followers_count'],
        profile_data['following_count'],
        profile_data['subscriptions_count'],
        int(profile_data['is_verified']) 
    ]]
    
    dmatrix = xgb.DMatrix(features)
    prediction = model.predict(dmatrix)
    
    # Adjust threshold
    return "Genuine" if prediction[0] >= 0.68 else "Fake"


def extract_profile_data(driver, username):
    try:
        driver.get(f"https://x.com/{username}/")
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        close_pop_up(driver)
        time.sleep(2)

        # Try multiple XPaths for user header
        user_header_xpaths = [
            "//div[contains(@data-testid, 'UserName')]",
            "//span[contains(@class, 'css-901oao') and contains(text(), '@')]"
        ]
        user_header = find_element_with_retry(driver, user_header_xpaths)

        if not user_header:
            print(f"User header not found for {username}.")
            return None

        # Multiple XPaths for followers count
        followers_count_xpaths = [
            "//a[contains(@href,'followers')]//span[1]",
            "//span[contains(@data-testid, 'followers')]"
            ]
        followers_count_elem = find_element_with_retry(driver, followers_count_xpaths)
        followers_count = parse_count(followers_count_elem.text) if followers_count_elem else 0

        # Multiple XPaths for following count
        following_count_xpaths = [
            "//a[contains(@href,'following')]//span[1]",
            "//span[contains(@data-testid, 'following')]"
        ]
        following_count_elem = find_element_with_retry(driver, following_count_xpaths)
        following_count = parse_count(following_count_elem.text) if following_count_elem else 0

        # Multiple XPaths for subscriptions count
        subscriptions_count_xpaths = [
            "//a[contains(@href,'subscriptions')]//span",
            "//span[contains(text(), 'Subscriptions')]"
        ]
        subscriptions_count_elem = find_element_with_retry(driver, subscriptions_count_xpaths)
        subscriptions_count = parse_count(subscriptions_count_elem.text) if subscriptions_count_elem else 0

        # Multiple XPaths for verified status
        verified_xpaths = [
            "//div[@id='react-root']//main//div[contains(@class, 'css-175oi2r')]//span[contains(@class, 'r-')]//div[1]",
            "//svg[@aria-label='Verified']"
        ]
        is_verified = bool(find_element_with_retry(driver, verified_xpaths))

        profile_data = {
            'username': username,
            'followers_count': followers_count,
            'following_count': following_count,
            'subscriptions_count': subscriptions_count,
            'is_verified': is_verified,
            'status': analyze_profile_data({
                'followers_count': followers_count,
                'following_count': following_count,
                'subscriptions_count': subscriptions_count,
                'is_verified': is_verified
            })
        }
        return profile_data

    except Exception as e:
        print(f"Error extracting profile data for {username}: {e}")
        return None

# Helper function to try multiple XPaths with retries
def find_element_with_retry(driver, xpaths, retries=1):
    for xpath in xpaths:
        try:
            element = driver.find_element(By.XPATH, xpath)
            if element:
                return element
        except Exception as e:
            print(f"XPath not found: {xpath}, retrying... Error: {e}")
            time.sleep(1)  # Optional: add a short delay before retrying
            continue
    return None


@app.route('/')
def home():
    return render_template('index.html')  # Serve the HTML file

@app.route('/monitor', methods=['POST'])


@app.route('/monitor', methods=['POST'])
def monitor_profiles():
    profiles = request.json.get('profiles', [])
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
            # Only append the status to the result (Fake or Genuine)
            results.append({
                'username': profile_data['username'],
                'status': profile_data['status']
            })
            print(f"Profile data for {username}: {profile_data['status']}")
        else:
            print(f"Failed to extract data for {username}.")
        
        time.sleep(random.uniform(5, 10))
    
    driver.quit()
    conn.close()
    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True)
