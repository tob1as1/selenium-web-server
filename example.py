import time
import asyncio
import discord
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor

TOKEN = "MTI5OTcwMzAzMzUyNDkxNjI5NQ.Gwf1mN.qDlXf68BcyOXkB3NQWcbCZTnuq2-RXmftq6bgM"  

client = discord.Client(intents=discord.Intents.default())
executor = ThreadPoolExecutor(max_workers=2)

WEBSITES = [
    {
        "url": "https://www.vinted.de/catalog?search_id=18338727003&time=1730656005&order=newest_first&search_text=nike%20&catalog[]=5&page=1",
        "channel_id": 1299753730912292925,
        "sleep_duration": 30,
        "name": "Nike"
    }
]


def setup_webdriver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("Driver korrekt gestartet!")
    return driver


def get_product_titles_sync(driver, website):
    driver.get(website)
    time.sleep(2)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    products = driver.find_elements(By.CLASS_NAME, "feed-grid__item")
    titles_and_links = []

    for product in products:
        try:
            title_element = product.find_element(By.CSS_SELECTOR, "a.new-item-box__overlay--clickable")
            link = title_element.get_attribute("href")
            title = title_element.get_attribute("title")
            titles_and_links.append((title, link))
        except Exception as e:
            print("Element konnte nicht gefunden werden:", e)
            continue
            
    return titles_and_links

async def get_product_titles(driver, website):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, get_product_titles_sync, driver, website)

async def monitor_website(website_data):
    url = website_data["url"]
    channel_id = website_data["channel_id"]
    sleep_duration = website_data["sleep_duration"]
    name = website_data["name"]
    
    driver = setup_webdriver()
    
    try:
        previous_titles = await get_product_titles(driver, url)
        print(f"Initiale Produkte für {name} geladen!")
        print(f"########### Wait {sleep_duration}s auf {name} ###########")
        await asyncio.sleep(sleep_duration)
        while True:
            current_products = await get_product_titles(driver, url)
            current_links = [link for _, link in current_products]
            previous_links = [link for _, link in previous_titles]

            if current_links and previous_links:
                first_previous_link = previous_links[0]
                if first_previous_link in current_links:
                    index_of_first_previous = current_links.index(first_previous_link)
                    products_above = current_products[:index_of_first_previous][::-1]
                    for title, link in products_above:
                        print(f"{title} - {link}")
                        channel = client.get_channel(channel_id)
                        if channel:
                            await channel.send(f"{title} - {link}")
                        await asyncio.sleep(1)

                previous_titles = current_products
            else:
                print(f"Keine neuen Produkte auf {name} Page gefunden")
            
            print(f"########### Wait {sleep_duration}s auf {name} ###########")
            await asyncio.sleep(sleep_duration)
    except KeyboardInterrupt:
        print(f"Monitoring für {name} beendet.")
    finally:
        driver.quit()  # Schließt den Webdriver am Ende des Monitorings
        print(f"Driver für {name} beendet.")

@client.event
async def on_ready():
    print(f"Eingeloggt als {client.user}")
    tasks = []
    
    # Tasks mit 10 Sekunden Abstand starten
    for website in WEBSITES:
        tasks.append(asyncio.create_task(monitor_website(website)))
        print(f"########### Task {website['name']} gestartet!")
        await asyncio.sleep(10)  
    
    await asyncio.gather(*tasks)

# Startet den Bot
client.run(TOKEN)
