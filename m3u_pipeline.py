import asyncio
from playwright.async_api import async_playwright
import time
import os

# --- UTILIDADES PARA GITHUB ACTIONS ---
def install_playwright_drivers():
    """Instala los drivers de navegador para Playwright."""
    print("-> Instalando drivers de Playwright...")
    os.system('playwright install chromium')

# --- ⚙️ LÓGICA DE SCRAPING DE PHOTOCALL TV ---
async def scrape_all_photocall_channels():
    """Extrae todas las URLs de stream de Photocall TV."""
    install_playwright_drivers() 
    
    m3u_lines = ['#EXTM3U\n']
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("-> Navegando a Photocall TV...")
        await page.goto("https://photocalltv.es/", timeout=60000)

        CHANNEL_SELECTOR = '.canales' # Selector CSS genérico.
        channel_elements = await page.locator(CHANNEL_SELECTOR).all()
        total_canales = len(channel_elements)
        print(f"-> Se encontraron {total_canales} posibles canales en Photocall TV.")

        for i, element in enumerate(channel_elements):
            try:
                canal_name = await element.get_attribute('id') or f"Canal_{i+1}"
                print(f"[{i+1}/{total_canales}] Procesando: {canal_name}")

                await element.click(timeout=5000)
                time.sleep(3) # Pausa ética

                url_stream = ""
                try:
                    new_page = await page.wait_for_event("popup", timeout=15000)
                    url_stream = new_page.url
                    await new_page.close()
                except Exception:
                    pass

                if url_stream and url_stream not in ["about:blank", "https://photocalltv.es/"]:
                    nombre_m3u = canal_name.replace("_", " ").title()
                    m3u_lines.append(f'#EXTINF:-1 tvg-name="{nombre_m3u}", {nombre_m3u}')
                    m3u_lines.append(f'{url_stream}\n')
                else:
                    print(f"   [FALLO] No se pudo obtener stream para {canal_name}.")
                
                await page.goto("https://photocalltv.es/", timeout=30000)
                
            except Exception:
                pass
                
        await browser.close()
        
    return m3u_lines

# --- 🚀 PUNTO DE ENTRADA ---
def run_scraper():
    # Ejecuta el scraping
    m3u_photocall = asyncio.run(scrape_all_photocall_channels()) 
    
    # Guarda la lista directamente en el archivo final para el commit
    filename = 'photocall_canales.m3u' 
    with open(filename, 'w') as f:
        f.writelines(m3u_photocall)
    print(f"-> Lista de Photocall TV guardada en {filename}")


if __name__ == '__main__':
    run_scraper()
