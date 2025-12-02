import asyncio
from playwright.async_api import async_playwright
import time
import os
import re # ¡Asegúrate de que esta línea esté al inicio!

# --- UTILIDADES PARA GITHUB ACTIONS ---
def install_playwright_drivers():
    """Instala los drivers de navegador (Chromium) necesarios para Playwright."""
    print("-> Instalando drivers de Playwright...")
    # La instalación se realiza automáticamente cuando Playwright se usa por primera vez.
    os.system('playwright install chromium') 

# --- ⚙️ LÓGICA DE SCRAPING DE PHOTOCALL TV ---
async def scrape_all_photocall_channels():
    """Extrae las URLs del stream navegando a las páginas internas y buscando el stream."""
    install_playwright_drivers() 
    
    m3u_lines = ['#EXTM3U\n']
    BASE_URL = "https://photocalltv.online/"
    
    async with async_playwright() as p:
        # Usamos 'args=["--no-sandbox"]' para asegurar la compatibilidad con GitHub Actions
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        
        print(f"-> Navegando a la URL base: {BASE_URL}")
        await page.goto(BASE_URL, timeout=60000)

        # 1. IDENTIFICAR TODOS LOS ENLACES DE CANAL (Búsqueda Universal)
        
        # Obtenemos TODOS los elementos <a> (links) en la página.
        all_links = await page.get_by_role('link').all()
        
        # Extraemos solo las URLs que contienen la palabra clave 'canal-' y que son únicas.
        channel_urls = set() # Usamos un set para evitar duplicados
        
        for element in all_links:
            href = await element.get_attribute('href')
            # Filtramos por el patrón de URL de canal y nos aseguramos de que no sean enlaces ancla
            if href and "/canal-" in href and not href.startswith('#'): 
                
                if href.startswith('http'):
                    # Si el enlace es absoluto, lo añadimos directamente (evita la duplicación)
                    channel_urls.add(href)
                else:
                    # Si el enlace es relativo, construimos la URL completa
                    channel_urls.add(BASE_URL.rstrip('/') + href.lstrip('/'))

        # Convertimos el set a list para poder iterar con índice
        channel_urls = list(channel_urls)
        
        # Eliminamos el enlace base de Photocalltv.Online si está en la lista de URLs
        try:
            channel_urls.remove(BASE_URL)
        except ValueError:
            pass 

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
                
                content = await page.content()
                
                # Buscamos la variable MAIN_HLS
                main_hls_match = re.search(r'const MAIN_HLS="([^"]+)"', content)
                if main_hls_match:
                    url_stream = main_hls_match.group(1)
                    print(f"   [INFO] Stream encontrado en variable MAIN_HLS.")
                
                # Si no se encuentra MAIN_HLS, buscamos BACKUP_HLS
                if not url_stream:
                    backup_hls_match = re.search(r'const BACKUP_HLS="([^"]+)"', content)
                    if backup_hls_match:
                        url_stream = backup_hls_match.group(1)
                        print(f"   [INFO] Stream encontrado en variable BACKUP_HLS.")

                # Si aún no se encuentra el stream, buscamos M3U8/M3U genérico
                if not url_stream:
                    m3u_match = re.search(r'(https?://[^\s\'"]+\.(m3u8|m3u))', content)
                    if m3u_match:
                        url_stream = m3u_match.group(1)
                        print(f"   [INFO] Stream encontrado con expresión regular M3U/M3U8.")


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
