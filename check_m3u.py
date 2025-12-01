import requests
import re
import os
from concurrent.futures import ThreadPoolExecutor

# --- Configuración ---
INPUT_M3U_FILE = 'lista_original.m3u'  # Cambia esto al nombre de tu archivo M3U en GitHub
OUTPUT_M3U_FILE = 'lista_limpia.m3u'
TIMEOUT = 10 # Tiempo máximo de espera para la respuesta del servidor (segundos)
MAX_WORKERS = 20 # Número de verificaciones de canales concurrentes


def parse_m3u(file_path):
    """Analiza el archivo M3U y devuelve una lista de tuplas (nombre, url)."""
    channels = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Expresión regular para encontrar parejas #EXTINF y URL
    matches = re.findall(r'(#EXTINF:.*?,(.*?)\n(.*?)\s*?)(?=\n#EXTINF|\Z)', content, re.DOTALL)

    for match in matches:
        # match[1] es el nombre del canal, match[2] es la URL
        url = match[2].strip()
        name = match[1].strip()
        if url and url.startswith(('http', 'https')):
            channels.append({'name': name, 'url': url, 'active': False})
    
    print(f"✅ Canales encontrados: {len(channels)}")
    return channels


def check_url_aggressive(channel):
    """Intenta verificar la URL del canal usando múltiples métodos."""
    url = channel['url']
    
    # 1. Método HEAD (más rápido)
    try:
        response = requests.head(url, timeout=TIMEOUT, allow_redirects=True, verify=False)
        # Códigos válidos para un stream (200 OK, 3xx Redirect)
        if 200 <= response.status_code < 400:
            channel['active'] = True
            print(f"  [ACTIVO - HEAD] {channel['name']}")
            return channel
    except requests.exceptions.RequestException:
        pass # Falló, probamos el siguiente método

    # 2. Método GET parcial (Verificar contenido inicial/headers)
    try:
        headers = {'Range': 'bytes=0-1024', 'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=TIMEOUT, headers=headers, allow_redirects=True, verify=False)
        
        if 200 <= response.status_code < 400:
            # Comprobar que el Content-Type sea de video/audio/m3u8
            content_type = response.headers.get('Content-Type', '').lower()
            if any(t in content_type for t in ['video', 'audio', 'mpegurl', 'stream']):
                channel['active'] = True
                print(f"  [ACTIVO - GET Range] {channel['name']}")
                return channel
    except requests.exceptions.RequestException:
        pass

    channel['active'] = False
    print(f"  [MUERTO] {channel['name']}")
    return channel


def update_m3u_file(channels):
    """Genera un nuevo archivo M3U solo con los canales activos."""
    active_channels = [c for c in channels if c['active']]
    
    content = "#EXTM3U\n"
    for channel in active_channels:
        content += f"#EXTINF:-1, {channel['name']}\n{channel['url']}\n"
    
    with open(OUTPUT_M3U_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"✅ Lista limpia generada: {len(active_channels)} canales activos guardados en {OUTPUT_M3U_FILE}")


def main():
    if not os.path.exists(INPUT_M3U_FILE):
        print(f"❌ Error: El archivo de entrada '{INPUT_M3U_FILE}' no se encuentra. ¡Verifica el nombre!")
        return

    channels = parse_m3u(INPUT_M3U_FILE)
    
    print(f"\n⚡ Iniciando verificación de {len(channels)} canales con {MAX_WORKERS} hilos concurrentes...")

    # Usar ThreadPoolExecutor para verificar canales en paralelo (muy rápido)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Mapear la función de verificación a la lista de canales
        results = list(executor.map(check_url_aggressive, channels))
        
    # El objeto 'results' ya tiene el estado 'active' actualizado
    update_m3u_file(results)
    print("\nProceso de automatización finalizado.")


if __name__ == "__main__":
    main()
