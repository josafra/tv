import asyncio
from playwright.async_api import async_playwright
import time
import os
import re

# --- UTILIDADES PARA GITHUB ACTIONS ---
def install_playwright_drivers():
    """Instala los drivers de navegador (Chromium) necesarios para Playwright."""
    print("-> Instalando drivers de Playwright...")
    os.system('playwright install chromium') 

# --- ⚙️ LÓGICA DE SCRAPING DE PHOTOCALL TV ---
async def scrape_all_photocall_channels():
    """Extrae las URLs del stream navegando a las páginas internas y buscando el stream."""
    install_playwright_drivers() 
    
    m3u_lines = ['#EXTM3U\n']
    BASE_URL = "https://photocalltv.online/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        
        print(f"-> Navegando a la URL base: {BASE_URL}")
        await page.goto(BASE_URL, timeout=60000)

        # =================================================================
        # 1. FORZAR LA CARGA DE CONTENIDO MEDIANTE SCROLL (SOLUCIÓN FINAL)
        # =================================================================
        print("-> Forzando la carga de todos los canales mediante scroll...")
        previous_height = -1
        max_scrolls = 10
        scroll_count = 0
        
        while scroll_count < max_scrolls:
            current_height = await page.evaluate("document.body.scrollHeight")
            
            if current_height == previous_height:
                break
                
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2) # Dar tiempo para que el JS cargue el nuevo contenido
            
            previous_height = current_height
            scroll_count += 1
        
        print(f"-> Scroll completado. Se realizaron {scroll_count} scrolls.")
        # =================================================================
        
        # 2. IDENTIFICAR TODOS LOS ENLACES DE CANAL (Búsqueda Universal)
        
        # Obtenemos TODOS los elementos <a> (links) en la página.
        all_links = await page.get_by_role('link').all()
        
        # Extraemos solo las URLs que contienen la palabra clave 'canal-' y que son únicas.
        channel_urls = set()
        
        for element in all_links:
            href = await element.get_attribute('href')
            if href and "/canal-" in href and not href.startswith('#'): 
                
                if href.startswith('http'):
                    channel_urls.add(href)
                else:
                    channel_urls.add(BASE_URL.rstrip('/') + href.lstrip('/'))

        channel_urls = list(channel_urls)
        
        try:
            channel_urls.remove(BASE_URL)
        except ValueError:
            pass 

        total_canales = len(channel_urls)
        # ESTE NÚMERO DEBERÍA SER AHORA MUCHO MAYOR (más de 100)
        print(f"-> Se encontraron {total_canales} URLs de canal para procesar.")

        # 3. PROCESAR CADA URL DE CANAL
        for i, channel_url in enumerate(channel_urls):
            
            url_stream = ""
            canal_name = channel_url.split('/')[-2].replace('-', ' ').title()
            print(f"[{i+1}/{total_canales}] Procesando: {canal_name} ({channel_url})")
            
            try:
                
                await page.goto(channel_url, timeout=45000)
                await asyncio.sleep(3) 

                # --- 4. EXTRACCIÓN ROBUSTA: BUSCANDO EL STREAM EN EL HTML/JAVASCRIPT ---
                
                content = await page.content()
                
                main_hls_match = re.search(r'const MAIN_HLS="([^"]+)"', content)
                if main_hls_match:
                    url_stream = main_hls_match.group(1)
                    print(f"   [INFO] Stream encontrado en variable MAIN_HLS.")
                
                if not url_stream:
                    backup_hls_match = re.search(r'const BACKUP_HLS="([^"]+)"', content)
                    if backup_hls_match:
                        url_stream = backup_hls_match.group(1)
                        print(f"   [INFO] Stream encontrado en variable BACKUP_HLS.")

                if not url_stream:
                    m3u_match = re.search(r'(https?://[^\s\'"]+\.(m3u8|m3u))', content)
                    if m3u_match:
                        url_stream = m3u_match.group(1)
                        print(f"   [INFO] Stream encontrado con expresión regular M3U/M3U8.")


                # --- 5. Formatea y añade a la lista ---
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
    
    filename = 'photocall_canales.m3u' 
    with open(filename, 'w') as f:
        f.writelines(m3u_photocall)
    print(f"-> Lista de Photocall TV guardada en {filename}")


if __name__ == '__main__':
    run_scraper()
