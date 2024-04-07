import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from .classify import classify_headline
# URL of the website to scrape
main_url = 'https://www.philstar.com/'

def get_soup(url):
    # Send a GET request to the URL
    response = requests.get(url)

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup

def get_headlines(url):
    soup = get_soup(url)

    # Find all occurrences of div with class="tiles late ribbon-cont"
    ribbon_containers = soup.find_all('div', class_='tiles late ribbon-cont')

    headlines = []

    # Iterate through each ribbon container
    for ribbon_cont in ribbon_containers:
        # Find all <a> tags within the specified CSS selector
        links = ribbon_cont.select('.ribbon .ribbon_content .ribbon_title a[href]')
        
        # Extract and print the href attribute of each <a> tag
        for link in links:
            href = link['href']
            headlines.append(href)
        
    return headlines

def headline_data(urls):
    headline_data = []

    for url in urls:
        soup = get_soup(url)
    
        # Find and extract headline title if present
        title_div = soup.find('div', class_='article__title')

        if not title_div:
            continue
        
        title = title_div.find('h1').text.strip()

        # Find and extract date and time
        date_time_str = soup.find('div', class_='article__date-published').text.strip()
        
       # Format date and time
        formatted_date_time = datetime.strptime(date_time_str, '%B %d, %Y | %I:%M%p')

        # Convert the datetime object to the desired timezone
        philippines_timezone = 'Asia/Manila'
        localized_time = pytz.timezone(philippines_timezone).localize(formatted_date_time)

        # Convert the localized time to a timestamp with timezone
        timestamp_with_timezone = localized_time.strftime('%Y-%m-%d %H:%M:%S.%f%z')

        # Classify disaster type using trained model
        disaster_type = classify_headline(title)['prediction']

        headline_data.append({
            'title': title,
            'link': url,
            'disaster_type': disaster_type,
            'posted_datetime': timestamp_with_timezone
        })
    
    return headline_data

def classified_headlines():
    links = get_headlines(main_url)    
    article_data = headline_data(links)

    return article_data
