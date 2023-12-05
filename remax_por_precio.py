import requests
from bs4 import BeautifulSoup
import pandas as pd
# import pyshorteners

productslist = []
index = 0
lower_price = '100000'
higher_price = '200000'
# shortener = pyshorteners.Shortener()


def get_data(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    return soup


def parse(soup):
    results = soup.find_all('div', {'class': 'container-card-prop ng-star-inserted'})

    if len(results) == 0:
        return

    for item in results:
        global index
        index += 1
        product = {
            'ID': index,
            'title': item.find('h2', {'class': 'description ng-star-inserted'}).text,
            'currency': '',
            'price': item.find('p', {'id': 'price'}).text.replace('.', '').strip(),
            'location': item.find('h2', {'class': 'description ng-star-inserted'}).text,
            'image': item.find('img')['src'],
            'links': item.find('a')['href']  # shortener.tinyurl.short(item['href'])
        }
        productslist.append(product)
    return productslist


def output(productslist, searchterm):
    productsdf = pd.DataFrame(productslist)
    file_name = searchterm + '_output.csv'
    productsdf.to_csv(file_name, index=False)
    print('Saved to CSV:' + file_name)
    return


def run():
    result = []

    url = f'https://www.remax.com.ar/listings/buy?page=0&pageSize=24&sort=-createdAt&in:operationId=1&in:typeId=9,10,11&pricein=1:{lower_price}:{higher_price}&filterCount=2&viewMode=list'
    soup = get_data(url)
    productslist = parse(soup)

    EOF = False
    i = 1
    while not EOF:
        i = i + 1
        url = f'https://www.remax.com.ar/listings/buy?page=1&pageSize=24&sort=-createdAt&in:operationId=1&in:typeId=9,10,11&pricein=1:{lower_price}:{higher_price}&filterCount={i}&viewMode=list'
        soup = get_data(url)
        result = parse(soup)

        if result is None or i > 500:
            EOF = True

    output(productslist, 'por_precio')


if __name__ == "__main__":
    run()
