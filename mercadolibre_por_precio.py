import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MercadoLibreInmueblesScraper:
    """
    Scraper optimizado para inmuebles de MercadoLibre Argentina
    """
    
    def __init__(self, min_price: str = "10000", max_price: str = "200000", delay: float = 1.0):
        self.min_price = min_price
        self.max_price = max_price
        self.delay = delay  # Delay entre requests para ser respetuoso
        self.base_url = "https://inmuebles.mercadolibre.com.ar"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.products_list = []
        
    def get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """
        Obtiene el contenido HTML de una URL y lo convierte en objeto BeautifulSoup
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error al obtener la página {url}: {e}")
            return None
    
    def extract_meters(self, item) -> Optional[float]:
        """
        Extrae los metros cuadrados del inmueble
        """
        try:
            # Buscar en los atributos de la lista
            attributes = item.find_all('li', {'class': 'poly-attributes-list__bar'})
            for attr in attributes:
                text = attr.get_text(strip=True)
                if 'm² cubiertos' in text or 'm²' in text:
                    meters_match = re.search(r'(\d+(?:\.\d+)?)', text)
                    if meters_match:
                        return float(meters_match.group(1))
            
            # Buscar en otros posibles contenedores
            attributes_alt = item.find_all('li', {'class': 'poly-attributes_list__item'})
            for attr in attributes_alt:
                text = attr.get_text(strip=True)
                if 'm²' in text:
                    meters_match = re.search(r'(\d+(?:\.\d+)?)', text)
                    if meters_match:
                        return float(meters_match.group(1))
                        
        except Exception as e:
            logger.warning(f"Error extrayendo metros: {e}")
        
        return None
    
    def extract_image_url(self, item) -> Optional[str]:
        """
        Extrae la URL de la imagen del inmueble
        """
        try:
            img = item.find('img')
            if img:
                # Priorizar data-src sobre src
                return img.get('data-src') or img.get('src')
        except Exception as e:
            logger.warning(f"Error extrayendo imagen: {e}")
        return None
    
    def extract_product_data(self, item, index: int) -> Optional[Dict]:
        """
        Extrae todos los datos de un producto inmueble
        """
        try:
            # Título
            title_elem = item.find('h3', {'class': 'poly-component__title-wrapper'})
            if not title_elem:
                title_elem = item.find('h2', {'class': 'poly-component__title'})
            title = title_elem.get_text(strip=True) if title_elem else "Sin título"
            
            # Moneda
            currency_elem = item.find('span', {'class': 'andes-money-amount__currency-symbol'})
            currency = currency_elem.get_text(strip=True) if currency_elem else ""
            
            # Precio
            price_elem = item.find('span', {'class': 'andes-money-amount__fraction'})
            price = ""
            if price_elem:
                price = price_elem.get_text(strip=True).replace('.', '').replace(',', '')
            
            # Ubicación
            location_elem = item.find('span', {'class': 'poly-component__location'})
            location = location_elem.get_text(strip=True) if location_elem else "Sin ubicación"
            
            # Metros cuadrados
            meters = self.extract_meters(item)
            
            # Imagen
            image_url = self.extract_image_url(item)
            
            # Link
            link_elem = item.find('a')
            link = ""
            if link_elem and link_elem.get('href'):
                link = urljoin(self.base_url, link_elem['href'])
            
            product = {
                'ID': index,
                'title': title,
                'currency': currency,
                'price': price,
                'location': location,
                'meters': meters,
                'image': image_url,
                'link': link
            }
            
            return product
            
        except Exception as e:
            logger.error(f"Error extrayendo datos del producto {index}: {e}")
            return None
    
    def parse_page(self, soup: BeautifulSoup, start_index: int) -> List[Dict]:
        """
        Parsea una página y extrae todos los productos
        """
        products = []
        
        # Buscar contenedores de productos
        results = soup.find_all('div', {'class': 'andes-card'})
        
        if not results:
            logger.warning("No se encontraron productos en esta página")
            return products
        
        logger.info(f"Encontrados {len(results)} productos en la página")
        
        for i, item in enumerate(results):
            product = self.extract_product_data(item, start_index + i + 1)
            if product:
                products.append(product)
                logger.debug(f"Producto extraído: {product['title'][:50]}...")
        
        return products
    
    def scrape_all_pages(self, max_pages: int = 20) -> List[Dict]:
        """
        Realiza el scraping de todas las páginas
        """
        all_products = []
        page = 0
        start_index = 0
        
        # Primera página
        url = f"{self.base_url}/venta/_PriceRange_{self.min_price}USD-{self.max_price}USD"
        logger.info(f"Iniciando scraping desde: {url}")
        
        soup = self.get_soup(url)
        if soup:
            products = self.parse_page(soup, start_index)
            all_products.extend(products)
            start_index += len(products)
            page += 1
        
        # Páginas siguientes
        while page < max_pages:
            offset = page * 48  # MercadoLibre usa incrementos de 48
            url = f"{self.base_url}/venta/_Desde_{offset + 1}_PriceRange_{self.min_price}USD-{self.max_price}USD"
            
            logger.info(f"Scrapeando página {page + 1}: {url}")
            
            soup = self.get_soup(url)
            if not soup:
                logger.warning(f"No se pudo obtener la página {page + 1}")
                break
            
            products = self.parse_page(soup, start_index)
            
            if not products:
                logger.info("No se encontraron más productos. Finalizando scraping.")
                break
            
            all_products.extend(products)
            start_index += len(products)
            page += 1
            
            # Delay entre requests para ser respetuoso
            time.sleep(self.delay)
        
        logger.info(f"Scraping completado. Total de productos: {len(all_products)}")
        return all_products
    
    def save_to_csv(self, products: List[Dict], filename: str = None):
        """
        Guarda los productos en un archivo CSV
        """
        if not products:
            logger.warning("No hay productos para guardar")
            return
        
        if not filename:
            filename = f"inmuebles_{self.min_price}-{self.max_price}USD.csv"
        
        try:
            df = pd.DataFrame(products)
            df.to_csv(filename, index=False, encoding='utf-8')
            logger.info(f"Datos guardados en: {filename}")
            
            # Mostrar estadísticas
            logger.info(f"Total de productos: {len(df)}")
            logger.info(f"Productos con precio: {df['price'].notna().sum()}")
            logger.info(f"Productos con metros: {df['meters'].notna().sum()}")
            
        except Exception as e:
            logger.error(f"Error guardando archivo CSV: {e}")
    
    def run(self, max_pages: int = 20, output_file: str = None):
        """
        Ejecuta el scraping completo
        """
        logger.info("Iniciando scraper de MercadoLibre Inmuebles")
        logger.info(f"Rango de precios: {self.min_price}USD - {self.max_price}USD")
        
        try:
            products = self.scrape_all_pages(max_pages)
            self.save_to_csv(products, output_file)
            return products
            
        except Exception as e:
            logger.error(f"Error durante el scraping: {e}")
            return []

def main():
    """
    Función principal para ejecutar el scraper
    """
    # Configuración
    MIN_PRICE = "200000"
    MAX_PRICE = "800000"
    MAX_PAGES = 15
    DELAY = 1.5  # segundos entre requests
    
    # Crear y ejecutar scraper
    scraper = MercadoLibreInmueblesScraper(
        min_price=MIN_PRICE,
        max_price=MAX_PRICE,
        delay=DELAY
    )
    
    products = scraper.run(max_pages=MAX_PAGES)
    
    if products:
        print(f"\n✅ Scraping completado exitosamente!")
        print(f"📊 Total de productos extraídos: {len(products)}")
        print(f"💾 Datos guardados en CSV")
    else:
        print("❌ No se pudieron extraer productos")

if __name__ == "__main__":
    main()