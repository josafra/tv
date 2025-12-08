import os
import requests
import json
import threading
from datetime import datetime

# --- CONFIGURACIÓN Y CONSTANTES ---

# 📌 URL de origen para la lista de películas de IPTV-ORG
MOVIES_SOURCE_URL = "https://iptv-org.github.io/iptv/categories/movies.m3u"

# 📌 Palabras clave para el filtrado de idioma (en minúsculas)
LATIN_KEYWORDS = [
    'español', 
    'castellano', 
    'hispano', 
    'latino', 
    'latinoamericano', 
    'iberoamericano', 
    'habla hispana',
    'habla española',
    'lengua española',
    'idioma español',
    'lengua castellana', 
    'idioma castellano',
    'castellanohablante', 
    'hablante de castellano',
    'spanish',  # Inglés de Español
    'es',       # Abreviatura de idioma
    'spain',    # Nombre de país
    'latam',    # LatAm (Latin America)
    'america',  # Para capturar Latin America
    'sur',      # South, para "Latin America South"
    'mexico'    # País común de contenido en español
]

TIMEOUT = 3 # Timeout de 3 segundos para la validación de enlaces
HISTORY_FILE = 'channels_history.json'

# Variables globales para el multithreading
url_status_cache = {}
lock = threading.Lock()

# --- FUNCIONES DE UTILIDAD Y VALIDACIÓN ---

def check_url_status(url):
    """
    Verifica el estado de una URL (link) usando un timeout.
    Utiliza caché para no verificar la misma URL varias veces.
    """
    with lock:
        if url in url_status_cache:
            return url_status_cache[url]
    
    try:
        # HEAD es más rápido ya que no descarga el cuerpo completo del contenido
        response = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        # Consideramos válido si el código de estado es menor que 400 (200 OK, 3xx Redirección)
        is_valid = response.status_code < 400 
    except requests.exceptions.RequestException:
        is_valid = False
    
    with lock:
        url_status_cache[url] = is_valid
    return is_valid

def is_latin_channel(line):
    """
    Verifica si una línea de metadatos M3U (#EXTINF) contiene alguna palabra clave 
    latina/española o indicador de idioma en atributos comunes.
    """
    line_lower = line.lower()
    
    # 0. RECHAZO EXPLICITO DE IDIOMA INGLES (Para evitar falsos positivos)
    if 'tvg-language="en"' in line_lower or 'english' in line_lower:
        return False
    
    # 1. Búsqueda de palabras clave en el texto completo (título y atributos)
    if any(keyword in line_lower for keyword in LATIN_KEYWORDS):
        return True
    
    # 2. Búsqueda explícita de atributos de idioma/país comunes en IPTV-ORG
    if ('tvg-language="es"' in line_lower or 
        'tvg-country="es"' in line_lower or 
        'tvg-country="mx"' in line_lower or # México
        'tvg-country="co"' in line_lower or # Colombia
        'tvg-country="ar"' in line_lower or # Argentina
        'tvg-country="cl"' in line_lower):  # Chile
        return True
        
    return False

def load_m3u_content(filepath):
    """Lee el contenido de un archivo M3U."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error al leer {filepath}: {e}")
        return None

def save_m3u_content(filepath, content):
    """Escribe el contenido filtrado en el archivo M3U."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        return True
    except Exception as e:
        print(f"❌ Error al guardar {filepath}: {e}")
        return False

# --- LÓGICA ESPECÍFICA PARA cine.m3u (FILTRADO LATINO) ---

def update_cine_m3u():
    """
    Descarga la lista de cine de IPTV-ORG, filtra por latinos/españoles,
    valida los enlaces y guarda el resultado en 'cine.m3u'.
    """
    print(f"\n-> Procesando lista cine.m3u (Fuente remota: {MOVIES_SOURCE_URL})")
    
    try:
        # Descargar la lista remota
        response = requests.get(MOVIES_SOURCE_URL, timeout=10)
        response.raise_for_status()
        raw_m3u_content = response.text
    except Exception as e:
        print(f"❌ Error al descargar la lista de origen: {e}")
        return 'cine.m3u', 0 

    lines = raw_m3u_content.split('\n')
    output_lines = ['#EXTM3U']
    valid_channels_count = 0
    validation_threads = []
    
    print("   ... Filtrando y programando validación de enlaces (Multithreading)")
    
    channels_to_validate = []

    # PASO 1: Filtrar por idioma y preparar para la validación
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF'):
            # APLICAMOS EL FILTRO LATINO/ESPAÑOL AQUÍ
            if is_latin_channel(line):
                if i + 1 < len(lines):
                    url = lines[i+1].strip()
                    channels_to_validate.append((line, url))
                    i += 2
                else:
                    i += 1
            else:
                i += 1 # No es latino, se salta
        else:
            i += 1

    # PASO 2: Ejecutar la validación multithreaded
    for line, url in channels_to_validate:
        thread = threading.Thread(target=lambda u: check_url_status(u), args=(url,))
        validation_threads.append(thread)
        thread.start()

    # Esperar a que todos los threads terminen
    for thread in validation_threads:
        thread.join()

    # PASO 3: Construir la lista final usando el caché de estados
    for line, url in channels_to_validate:
        if url_status_cache.get(url, False):
            output_lines.append(line)
            output_lines.append(url)
            valid_channels_count += 1
            
    # Escribir el resultado
    save_m3u_content('cine.m3u', output_lines)
        
    print(f"✅ 'cine.m3u' actualizado con {valid_channels_count} canales latinos válidos.")
    return 'cine.m3u', valid_channels_count

# --- LÓGICA ORIGINAL PARA OTRAS LISTAS LOCALES ---

def process_local_m3u(filename):
    """
    Procesa un archivo M3U local existente (excepto cine.m3u), 
    validando todos sus enlaces y eliminando los caídos.
    """
    print(f"\n-> Procesando lista local: {filename}")
    content = load_m3u_content(filename)
    if not content:
        return filename, 0

    lines = content.split('\n')
    output_lines = ['#EXTM3U']
    valid_channels_count = 0
    
    validation_threads = []
    channels_to_validate = []

    # PASO 1: Identificar canales para validar
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF'):
            if i + 1 < len(lines):
                url = lines[i+1].strip()
                channels_to_validate.append((line, url))
                i += 2
            else:
                i += 1
        else:
            i += 1

    # PASO 2: Ejecutar la validación multithreaded
    for line, url in channels_to_validate:
        thread = threading.Thread(target=lambda u: check_url_status(u), args=(url,))
        validation_threads.append(thread)
        thread.start()

    # Esperar a que todos los threads terminen
    for thread in validation_threads:
        thread.join()

    # PASO 3: Construir la lista final
    for line, url in channels_to_validate:
        if url_status_cache.get(url, False):
            output_lines.append(line)
            output_lines.append(url)
            valid_channels_count += 1
            
    # Escribir el resultado
    save_m3u_content(filename, output_lines)
    
    print(f"✅ '{filename}' limpiado. Canales válidos: {valid_channels_count}.")
    return filename, valid_channels_count

# --- GESTIÓN DEL HISTORIAL ---

def save_history(data):
    """Guarda el historial de canales en channels_history.json."""
    try:
        # Aseguramos que solo se guarden números, como se corrigió previamente.
        cleaned_data = {k: v for k, v in data.items()} 
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=4)
        print("✅ Historial de canales actualizado.")
    except Exception as e:
        print(f"❌ Error al guardar el historial: {e}")

# --- FLUJO PRINCIPAL ---

def main():
    global url_status_cache 
    url_status_cache = {} 
    new_channels_data = {}

    # 1. 🎬 PROCESAR LISTA CINE.M3U (Implementación del filtro latino/español)
    cine_file, count = update_cine_m3u()
    new_channels_data[cine_file] = count
    
    # 2. 🌍 PROCESAR OTRAS LISTAS LOCALES
    # Obtener todas las listas M3U en el repositorio, excluyendo la que ya procesamos.
    all_m3u_files = [f for f in os.listdir('.') if f.endswith('.m3u')]
    m3u_files_to_process = [f for f in all_m3u_files if f != cine_file]
    
    for filename in m3u_files_to_process:
        # Se ejecuta la lógica original de validación para las demás listas
        filename, count = process_local_m3u(filename)
        new_channels_data[filename] = count

    # 3. 💾 GUARDAR EL NUEVO HISTORIAL
    save_history(new_channels_data)
    
    print("\nProceso de validación de listas terminado.")

if __name__ == "__main__":
    main()
