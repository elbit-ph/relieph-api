import pytz
import requests

from bs4 import BeautifulSoup
from datetime import datetime
from .classify import classify_headline

main_url = 'https://www.philstar.com/'

def get_soup(url):
    response = requests.get(url)

    soup = BeautifulSoup(response.content, 'html.parser')
    return soup

def get_headlines(url):
    soup = get_soup(url)

    ribbon_containers = soup.find_all('div', class_='tiles late ribbon-cont')

    headlines = []

    for ribbon_cont in ribbon_containers:
        links = ribbon_cont.select('.ribbon .ribbon_content .ribbon_title a[href]')
        
        for link in links:
            href = link['href']
            headlines.append(href)
        
    return headlines

def headline_data(urls):
    headline_data = []

    for url in urls:
        soup = get_soup(url)
    
        title_div = soup.find('div', class_='article__title')
        if not title_div:
            continue
        
        title = title_div.find('h1').text.strip()

        date_time_str = soup.find('div', class_='article__date-published').text.strip()
        
        formatted_date_time = datetime.strptime(date_time_str, '%B %d, %Y | %I:%M%p')

        localized_time = pytz.timezone('Asia/Manila').localize(formatted_date_time)

        disaster_type = classify_headline(title)['prediction']

        headline_data.append({
            'title': title,
            'link': url,
            'disaster_type': disaster_type,
            'posted_datetime': localized_time
        })
    
    return headline_data

def classified_headlines():
    links = get_headlines(main_url)    
    article_data = headline_data(links)

    return article_data
