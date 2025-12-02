import asyncio
from playwright.async_api import async_playwright
import time
import os
import re # ¡Añadido para las expresiones regulares!

# --- UTILIDADES PARA GITHUB ACTIONS ---
def install_playwright_drivers():
    """Instala los drivers de navegador (Chromium) necesarios para Playwright."""
    print("-> Instalando drivers de Playwright...")
    # La instalación se realiza automáticamente cuando Playwright se usa por primera vez, 
    # pero mantenemos la línea para asegurar la disponibilidad en entornos como GitHub Actions.
    os.system('playwright install chromium') 

# --- ⚙️ LÓGICA DE SCRAPING DE PHOTOCALL TV ---
async def scrape_all_photocall_channels():
    """Extrae las URLs del stream navegando a las páginas internas y buscando el stream."""
    install_playwright_drivers() 
    
    m3u_lines = ['#EXTM3U\n']
    
    async with async_playwright() as p:
        # Usamos 'args=["--no-sandbox"]' para asegurar la compatibilidad con GitHub Actions
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        
        BASE_URL = "https://photocalltv.online/"
        print(f"-> Navegando a la URL base: {BASE_URL}")
        await page.goto(BASE_URL, timeout=60000)

        # 1. IDENTIFICAR TODOS LOS ENLACES DE CANAL (Selector Corregido)
        # Este selector funciona para los elementos de Kadence Blocks que contienen el enlace.
        CHANNEL_LINK_SELECTOR = '.entry-content a'
        
        # Obtenemos TODOS los enlaces de canal (href)
        href_elements = await page.locator(CHANNEL_LINK_SELECTOR).all()
        
        # Extraemos las URLs de las páginas de canal
        channel_urls = []
        for element in href_elements:
            href = await element.get_attribute('href')
            if href and "canal-" in href:
                # Si el href es una URL absoluta, la usamos directamente. 
                # Si es relativa, la construimos. Esto evita la duplicación de la URL base.
                if href.startswith('http'):
                    channel_urls.append(href)
                else:
                    channel_urls.append(BASE_URL.rstrip('/') + '/' + href.lstrip('/'))


        total_canales = len(channel_urls)
        print(f"-> Se encontraron {total_canales} URLs de canal para procesar.")

        # 2. PROCESAR CADA URL DE CANAL
        for i, channel_url in enumerate(channel_urls):
            
            url_stream = ""
            # Intentamos extraer el nombre del canal de la URL
            canal_name = channel_url.split('/')[-2].replace('-', ' ').title()
            print(f"[{i+1}/{total_canales}] Procesando: {canal_name} ({channel_url})")
            
            try:
                
                # Navega directamente a la página del canal
                await page.goto(channel_url, timeout=45000)
                
                # Esperamos 3 segundos para que el JavaScript cargue y ejecute el reproductor
                await asyncio.sleep(3) 

                # --- 3. EXTRACCIÓN ROBUSTA: BUSCANDO EL STREAM EN EL HTML/JAVASCRIPT ---
                
                # Opción 1: Buscar directamente en el código fuente de la página por la URL HLS/M3U
                content = await page.content()
                
                # Expresión regular para encontrar cualquier URL que termine en .m3u8 o .m3u 
                # y que parezca ser un stream
                m3u_match = re.search(r'(https?://[^\s\'"]+\.(m3u8|m3u))', content)
                if m3u_match:
                    url_stream = m3u_match.group(1)
                
                # Opción 2: Buscar variables JS específicas (seguro que una de las dos funciona)
                if not url_stream:
                    # Buscamos la variable MAIN_HLS
                    main_hls_match = re.search(r'const MAIN_HLS="([^"]+)"', content)
                    if main_hls_match:
                        url_stream = main_hls_match.group(1)
                        print(f"   [INFO] Stream encontrado en variable MAIN_HLS.")
                
                if not url_stream:
                    # Buscamos la variable BACKUP_HLS
                    backup_hls_match = re.search(r'const BACKUP_HLS="([^"]+)"', content)
                    if backup_hls_match:
                        url_stream = backup_hls_match.group(1)
                        print(f"   [INFO] Stream encontrado en variable BACKUP_HLS.")


                # --- 4. Formatea y añade a la lista ---
                if url_stream and url_stream.startswith('http'):
                    print(f"   [ÉXITO] Stream capturado para {canal_name}.")
                    m3u_lines.append(f'#EXTINF:-1, {canal_name}')
                    m3u_lines.append(f'{url_stream}\n')
                else:
                    print(f"   [FALLO] No se pudo obtener un stream válido (http) para {canal_name}.")
                
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
