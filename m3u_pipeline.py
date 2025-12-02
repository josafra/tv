import asyncio
from playwright.async_api import async_playwright
import time
import os

# --- UTILIDADES PARA GITHUB ACTIONS ---
def install_playwright_drivers():
    """Instala los drivers de navegador (Chromium) necesarios para Playwright."""
    print("-> Instalando drivers de Playwright...")
    os.system('playwright install chromium')

# --- ⚙️ LÓGICA DE SCRAPING DE PHOTOCALL TV ---
async def scrape_all_photocall_channels():
    """Extrae las URLs del stream navegando a las páginas internas e interceptando el tráfico."""
    install_playwright_drivers() 
    
    m3u_lines = ['#EXTM3U\n']
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        BASE_URL = "https://photocalltv.online/"
        print(f"-> Navegando a la URL base: {BASE_URL}")
        await page.goto(BASE_URL, timeout=60000)

        # 1. IDENTIFICAR TODOS LOS ENLACES DE CANAL
        # Usamos el selector más probable para los enlaces (<a>) dentro de los contenedores (<li>).
        # SI ESTO FALLA, DEBE CAMBIARSE A MANO:
        CHANNEL_LINK_SELECTOR = '.kb-advanced-heading-link' 
        
        # Obtenemos TODOS los enlaces de canal (href)
        href_elements = await page.locator(CHANNEL_LINK_SELECTOR).all()
        
        # Extraemos las URLs de las páginas de canal
        channel_urls = []
        for element in href_elements:
            href = await element.get_attribute('href')
            if href and "canal-" in href:
                # Construye la URL completa
                channel_urls.append(BASE_URL.rstrip('/') + '/' + href.lstrip('/'))

        total_canales = len(channel_urls)
        print(f"-> Se encontraron {total_canales} URLs de canal para procesar.")

        # 2. PROCESAR CADA URL DE CANAL
        for i, channel_url in enumerate(channel_urls):
            
            # Inicializamos la variable que contendrá la URL final del stream
            url_stream = ""
            canal_name = channel_url.split('/')[-2].replace('-', ' ').title()
            print(f"[{i+1}/{total_canales}] Procesando: {canal_name} ({channel_url})")
            
            try:
                # --- 3. CONFIGURACIÓN DE LA INTERCEPTACIÓN DE RED ---
                
                # Función que se ejecuta cada vez que hay una petición de red
                async def capture_request(route, request):
                    nonlocal url_stream
                    request_url = request.url
                    
                    # Buscamos streams M3U8, MP4, o M3U. El not url_stream evita sobrescribir
                    if any(ext in request_url for ext in ['.m3u8', '.mp4', '.m3u']) and not url_stream:
                        url_stream = request_url
                        # Opcional: detenemos la intercepción si encontramos el stream
                        await page.unroute("**/*")
                    
                    # Siempre debe continuar la petición para que la página cargue
                    await route.continue_()

                # Comenzamos a interceptar todas las peticiones antes de navegar/recargar
                await page.route("**/*", capture_request)
                
                # Navega directamente a la página del canal para iniciar la carga del stream
                await page.goto(channel_url, timeout=45000)
                
                # Esperamos un tiempo suficiente para que el reproductor cargue y haga la petición M3U8
                await asyncio.sleep(8) 
                
                # Aseguramos que la intercepción se detenga si no se detuvo antes
                await page.unroute("**/*")

                # --- 4. Formatea y añade a la lista ---
                if url_stream:
                    m3u_lines.append(f'#EXTINF:-1, {canal_name}')
                    m3u_lines.append(f'{url_stream}\n')
                else:
                    print(f"   [FALLO] No se pudo obtener stream (URL final) para {canal_name}.")
                
            except Exception as e:
                print(f"   [ERROR] Fallo al procesar {canal_name}: {e}")
                
        await browser.close()
        
    return m3u_lines

# --- 🚀 PUNTO DE ENTRADA Y GUARDADO ---

def run_scraper():
    """Ejecuta el scraper y guarda el resultado en el archivo final."""
    
    m3u_photocall = asyncio.run(scrape_all_photocall_channels()) 
    
    # Guarda la lista en el archivo final para el commit (photocall_canales.m3u)
    filename = 'photocall_canales.m3u' 
    with open(filename, 'w') as f:
        f.writelines(m3u_photocall)
    print(f"-> Lista de Photocall TV guardada en {filename}")


if __name__ == '__main__':
    run_scraper()
