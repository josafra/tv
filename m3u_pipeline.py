import asyncio
from playwright.async_api import async_playwright
import time
import os

# --- UTILIDADES PARA GITHUB ACTIONS ---
def install_playwright_drivers():
    """
    Instala los drivers de navegador (Chromium) necesarios para Playwright.
    Este paso es crucial para que funcione en el servidor de GitHub.
    """
    print("-> Instalando drivers de Playwright...")
    os.system('playwright install chromium')

# --- ⚙️ LÓGICA DE SCRAPING DE PHOTOCALL TV ---
async def scrape_all_photocall_channels():
    """
    Navega a Photocall TV, hace clic en TODOS los logos y extrae las URLs de stream.
    """
    install_playwright_drivers() 
    
    # El encabezado M3U debe ir primero
    m3u_lines = ['#EXTM3U\n']
    
    async with async_playwright() as p:
        # Lanza el navegador en modo headless (sin interfaz gráfica)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("-> Navegando a Photocall TV...")
        await page.goto("https://photocalltv.es/", timeout=60000)

        # 1. IDENTIFICAR TODOS LOS CANALES CLICABLES
        # Si esto falla, debes ajustar este selector a la clase CSS o ID correcta.
        CHANNEL_SELECTOR = '.canales-li' 
        
        channel_elements = await page.locator(CHANNEL_SELECTOR).all()
        total_canales = len(channel_elements)
        print(f"-> Se encontraron {total_canales} posibles canales en Photocall TV.")

        for i, element in enumerate(channel_elements):
            try:
                canal_name = await element.get_attribute('id') or f"Canal_{i+1}"
                print(f"[{i+1}/{total_canales}] Procesando: {canal_name}")

                # 2. Simular el clic en el logo
                await element.click(timeout=5000)
                time.sleep(3) # Pausa ética y de carga

                # 3. Intentar capturar la URL del stream
                url_stream = ""
                try:
                    # Espera la ventana emergente que contiene el stream
                    new_page = await page.wait_for_event("popup", timeout=15000)
                    url_stream = new_page.url
                    await new_page.close()
                except Exception:
                    # Si no hay pop-up o falla la espera, no se captura la URL
                    pass

                # 4. Formatea y añade a la lista (Formato M3U SIMPLE, sin logos)
                if url_stream and url_stream not in ["about:blank", "https://photocalltv.es/"]:
                    # Formatea el nombre del canal
                    nombre_m3u = canal_name.replace("_", " ").title()
                    
                    # Añade la etiqueta #EXTINF simple
                    m3u_lines.append(f'#EXTINF:-1, {nombre_m3u}')
                    # Añade la URL del stream
                    m3u_lines.append(f'{url_stream}\n')
                else:
                    print(f"   [FALLO] No se pudo obtener stream para {canal_name}.")
                
                # 5. Vuelve a la página principal para el siguiente clic
                await page.goto("https://photocalltv.es/", timeout=30000)
                
            except Exception as e:
                # Captura errores en canales individuales
                print(f"   [ERROR] Fallo al procesar {canal_name}: {e}")
                
        await browser.close()
        
    return m3u_lines

# --- 🚀 PUNTO DE ENTRADA Y GUARDADO ---

def run_scraper():
    """Ejecuta el scraper y guarda el resultado en el archivo final."""
    
    # 1. Ejecuta la función asíncrona principal
    m3u_photocall = asyncio.run(scrape_all_photocall_channels()) 
    
    # 2. Guarda la lista en el archivo final para el commit
    filename = 'photocall_canales.m3u' 
    with open(filename, 'w') as f:
        f.writelines(m3u_photocall)
    print(f"-> Lista de Photocall TV guardada en {filename}")


if __name__ == '__main__':
    run_scraper()
