import requests
from bs4 import BeautifulSoup
import pandas as pd
# import pyshorteners

productslist = []
index = 0
lower_price = '10000'
higher_price = '200000'
# shortener = pyshorteners.Shortener()


def get_data(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    return soup


def parse(soup):
    results = soup.find_all('div', {'class': 'andes-card'})

    if len(results) == 0:
        return

    for item in results:
        global index
        index += 1
        product = {
            'ID': index,
            'title': item.find('h2', {'class': 'ui-search-item__title'}).text,
            'currency': item.find('span', {'class': 'andes-money-amount__currency-symbol'}).text,
            'price': item.find('span', {'class': 'andes-money-amount__fraction'}).text.replace('.', '').strip(),
            'location': item.find('span', {'class': 'ui-search-item__location-label'}).text,
            'image': item.find('img')['data-src'],
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

    url = f'https://inmuebles.mercadolibre.com.ar/venta/_PriceRange_{lower_price}USD-{higher_price}USD'
    soup = get_data(url)
    productslist = parse(soup)

    EOF = False
    i = 1
    while not EOF:
        i = i + 48
        url = f'https://inmuebles.mercadolibre.com.ar/casas/venta/_Desde_{i}_PriceRange_{lower_price}USD-{higher_price}USD'
        soup = get_data(url)
        result = parse(soup)

        if result is None or i > 500:
            EOF = True

    output(productslist, 'por_precio')


if __name__ == "__main__":
    run()
