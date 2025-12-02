import asyncio
from playwright.async_api import async_playwright
import time
import os

# --- UTILIDADES PARA GITHUB ACTIONS ---

def install_playwright_drivers():
    """Instala los drivers de navegador para Playwright en el servidor de GitHub."""
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
        await page.goto("https://photocalltv.es/", timeout=60000)

        # Selector CSS para TODOS los logos. Ajuste esto si falla.
        CHANNEL_SELECTOR = '.canales' 
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
                
            except Exception as e:
                print(f"   [ERROR] Fallo al procesar {canal_name}")
                
        await browser.close()
        
    return m3u_lines

# --- 🎯 SU FUNCIÓN DE PIPELINE PRINCIPAL (Debe adaptar sus funciones aquí) ---

# Sustituya las siguientes funciones con su lógica real
def load_existing_m3u():
    # Implemente su lógica para cargar otras listas M3U aquí
    return ['#EXTM3U\n', '#EXTINF:-1, Ejemplo Canal Propio\nhttp://ejemplo.com/stream\n']

def verify_all(m3u_list):
    # Implemente su lógica de verificación de enlaces activos aquí
    print(f"-> Verificando {len(m3u_list)} entradas...")
    return m3u_list # Devuelve la lista verificada

def write_m3u_file(m3u_list):
    # Implemente su lógica para guardar el archivo final
    filename = 'canales_final.m3u' # ¡Usaremos este nombre en main.yml!
    with open(filename, 'w') as f:
        f.writelines(m3u_list)
    print(f"-> Lista final guardada en {filename}")


# --- 🚀 PUNTO DE ENTRADA ---

def run_m3u_pipeline():
    # 1. Carga de listas M3U existentes
    m3u_original = load_existing_m3u()
    
    # 2. Scraping de Photocall TV
    m3u_photocall = asyncio.run(scrape_all_photocall_channels()) 

    # 3. Combinación y desduplicación (opcional)
    # Excluimos el encabezado '#EXTM3U\n' de la lista original si ya está en la de Photocall
    if len(m3u_original) > 0 and m3u_original[0].startswith('#EXTM3U'):
        m3u_original = m3u_original[1:]

    lista_final = ['#EXTM3U\n'] + m3u_original + m3u_photocall[1:]
    
    # 4. Verificación y guardado
    final_verified_list = verify_all(lista_final) 
    write_m3u_file(final_verified_list)


if __name__ == '__main__':
    run_m3u_pipeline()
