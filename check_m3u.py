import requests
import re
import os
from concurrent.futures import ThreadPoolExecutor

# --- Configuración ---
TIMEOUT = 10 # Tiempo máximo de espera para la respuesta del servidor (segundos)
MAX_WORKERS = 20 # Número de verificaciones de canales concurrentes

# Mapeo: URL Externa de IPTV-ORG (Fuente) -> Nombre del archivo local (Destino)
MAPPING_FILES = {
    # LATAM y España - ¡El script sobrescribirá estos archivos locales!
    'https://iptv-org.github.io/iptv/countries/es.m3u': 'espana.m3u',
    'https://iptv-org.github.io/iptv/countries/ar.m3u': 'argentina.m3u',
    'https://iptv-org.github.io/iptv/countries/mx.m3u': 'mexico.m3u',
    'https://iptv-org.github.io/iptv/countries/co.m3u': 'colombia.m3u',
    'https://iptv-org.github.io/iptv/countries/cl.m3u': 'chile.m3u',
    'https://iptv-org.github.io/iptv/countries/pe.m3u': 'peru.m3u',
    'https://iptv-org.github.io/iptv/countries/ve.m3u': 'venezuela.m3u',
    'https://iptv-org.github.io/iptv/countries/ec.m3u': 'ecuador.m3u',
    'https://iptv-org.github.io/iptv/countries/do.m3u': 'republicadominicana.m3u',
    'https://iptv-org.github.io/iptv/countries/cu.m3u': 'cuba.m3u',
    'https://iptv-org.github.io/iptv/countries/gt.m3u': 'guatemala.m3u',
    'https://iptv-org.github.io/iptv/countries/hn.m3u': 'honduras.m3u',
    'https://iptv-org.github.io/iptv/countries/sv.m3u': 'elsalvador.m3u',
    'https://iptv-org.github.io/iptv/countries/ni.m3u': 'nicaragua.m3u',
    'https://iptv-org.github.io/iptv/countries/cr.m3u': 'costarica.m3u',
    'https://iptv-org.github.io/iptv/countries/pa.m3u': 'panama.m3u',
    'https://iptv-org.github.io/iptv/countries/pr.m3u': 'puertorico.m3u',
    'https://iptv-org.github.io/iptv/countries/py.m3u': 'paraguay.m3u',
    'https://iptv-org.github.io/iptv/countries/uy.m3u': 'uruguay.m3u',
    'https://iptv-org.github.io/iptv/countries/bo.m3u': 'bolivia.m3u',
}


def get_m3u_content(source):
    """Obtiene el contenido M3U de una URL externa."""
    print(f"🌐 Descargando contenido de: {source}")
    try:
        # Petición GET para descargar el contenido del archivo M3U
        response = requests.get(source, timeout=TIMEOUT)
        response.raise_for_status() # Lanza error para códigos 4xx/5xx
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al descargar {source}: {e}")
        return None


def parse_m3u(content):
    """Analiza la cadena de texto M3U y devuelve una lista de tuplas (nombre, url, extinf)."""
    channels = []
    
    # Expresión regular para encontrar parejas #EXTINF y URL
    # Usamos re.DOTALL para que '.' incluya saltos de línea
    matches = re.findall(r'(#EXTINF:.*?,(.*?)\n(.*?)\s*?)(?=\n#EXTINF|\Z)', content, re.DOTALL)

    for match in matches:
        url = match[2].strip()
        name = match[1].strip()
        
        # match[0] contiene la línea #EXTINF y match[2] es la URL.
        # Guardamos match[0].split('\n')[0].strip() para obtener solo la línea #EXTINF original.
        if url and url.startswith(('http', 'https')):
            channels.append({
                'name': name, 
                'url': url, 
                'active': False, 
                'extinf': match[0].split('\n')[0].strip()
            })
    
    print(f"✅ Canales encontrados: {len(channels)}")
    return channels


def check_url_aggressive(channel):
    """Intenta verificar la URL del canal usando múltiples métodos (HEAD, GET parcial)."""
    url = channel['url']
    
    # Método 1: HEAD Request (más rápido)
    try:
        # verify=False se usa para evitar problemas con certificados SSL en algunos streams
        response = requests.head(url, timeout=TIMEOUT, allow_redirects=True, verify=False)
        # Códigos válidos para un stream (200 OK, 3xx Redirect)
        if 200 <= response.status_code < 400:
            channel['active'] = True
            print(f"  [ACTIVO - HEAD] {channel['name']}")
            return channel
    except requests.exceptions.RequestException:
        pass 

    # Método 2: GET parcial (Verificar contenido inicial/headers)
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

    # Si ninguno funciona
    channel['active'] = False
    print(f"  [MUERTO] {channel['name']}")
    return channel


def update_m3u_file(file_path, channels):
    """Genera un nuevo archivo M3U solo con los canales activos, sobrescribiendo el archivo de destino."""
    
    # Esta línea usa file_path (ej. 'argentina.m3u') como nombre de salida
    output_file = file_path 
    
    active_channels = [c for c in channels if c['active']]
    
    # El contenido M3U debe empezar con #EXTM3U
    content = "#EXTM3U\n"
    for channel in active_channels:
        # Usamos el #EXTINF original para preservar información (TVG-ID, logo, etc.)
        content += f"{channel['extinf']}\n{channel['url']}\n"
    
    # Guardar el contenido en el archivo local, sobrescribiéndolo
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"✅ Lista limpia generada: {len(active_channels)} canales activos guardados en {output_file}")


def main():
    print("Iniciando proceso de verificación masiva de archivos M3U...")

    for input_url, output_file_name in MAPPING_FILES.items():
        print(f"\n--- Procesando {output_file_name} (Fuente: {input_url}) ---")
        
        # Paso 1: Descargar el contenido M3U
        m3u_text = get_m3u_content(input_url)
        if not m3u_text:
            print("Saltando verificación debido a error de descarga.")
            continue
            
        # Paso 2: Analizar el contenido
        channels = parse_m3u(m3u_text)
        
        if not channels:
            print("No se encontraron canales válidos para verificar. Saltando.")
            continue

        print(f"⚡ Iniciando verificación de {len(channels)} canales con {MAX_WORKERS} hilos concurrentes...")
        # 

[Image of multithreading in Python]


        # Paso 3: Verificar Canales en paralelo
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # La función map aplica check_url_aggressive a cada canal
            results = list(executor.map(check_url_aggressive, channels))
            
        # Paso 4: Sobrescribir el archivo local
        update_m3u_file(output_file_name, results) 

    print("\nProceso de automatización finalizado.")


if __name__ == "__main__":
    main()
