import os
import requests
import json
import threading
from datetime import datetime

# --- CONFIGURACIÓN Y CONSTANTES ---

# 📌 Fuentes Remotas de IPTV-ORG para la actualización de listas de países
# {URL remota: Nombre del archivo local}
COUNTRY_SOURCES = {
    'https://iptv-org.github.io/iptv/countries/es.m3u': 'espana.m3u',
    'https://iptv-org.github.io/iptv/countries/ar.m3u': 'Argentina.m3u',
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

# 📌 Fuente Específica para Cine (Requiere filtro de idioma)
MOVIES_SOURCE_URL = "https://iptv-org.github.io/iptv/categories/movies.m3u"
CINE_FILENAME = "cine.m3u"

# 📌 Palabras clave para el filtrado de idioma (solo usado en cine.m3u)
LATIN_KEYWORDS = [
    'español', 'castellano', 'hispano', 'latino', 'latinoamericano', 
    'iberoamericano', 'habla hispana', 'habla española', 'lengua española', 
    'idioma español', 'lengua castellana', 'idioma castellano', 
    'castellanohablante', 'hablante de castellano', 'spanish', 'es', 'spain', 
    'latam', 'america', 'sur', 'mexico'
]

TIMEOUT = 3 # Timeout de 3 segundos para la validación de enlaces
HISTORY_FILE = 'channels_history.json'

# Variables globales para el multithreading
url_status_cache = {}
lock = threading.Lock()

# --- FUNCIONES DE UTILIDAD Y VALIDACIÓN ---

def check_url_status(url):
    """
    Verifica el estado de una URL (link) usando un timeout (3 segundos).
    Utiliza caché para no verificar la misma URL varias veces.
    """
    with lock:
        if url in url_status_cache:
            return url_status_cache[url]
    
    try:
        response = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
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
    (Sólo se usa para filtrar la lista de CINE)
    """
    line_lower = line.lower()
    
    # 0. RECHAZO EXPLICITO DE IDIOMA INGLES
    if 'tvg-language="en"' in line_lower or 'english' in line_lower:
        return False
    
    # 1. Búsqueda de palabras clave en el texto completo
    if any(keyword in line_lower for keyword in LATIN_KEYWORDS):
        return True
    
    # 2. Búsqueda explícita de atributos de idioma/país
    if ('tvg-language="es"' in line_lower or 
        'tvg-country="es"' in line_lower or 
        'tvg-country="mx"' in line_lower or 
        'tvg-country="co"' in line_lower or 
        'tvg-country="ar"' in line_lower or 
        'tvg-country="cl"' in line_lower): 
        return True
        
    return False

def save_m3u_content(filepath, content):
    """Escribe el contenido filtrado en el archivo M3U."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        return True
    except Exception as e:
        print(f"❌ Error al guardar {filepath}: {e}")
        return False

# --- LÓGICA DE PROCESAMIENTO GENERAL ---

def process_remote_list(source_url, filename, apply_latin_filter=False):
    """
    Descarga una lista remota, la filtra (si es cine), valida los enlaces 
    y guarda el resultado en el archivo local.
    """
    print(f"\n-> Procesando {filename} (Fuente remota: {source_url})")
    
    # 1. DESCARGA EL CONTENIDO REMOTO
    try:
        response = requests.get(source_url, timeout=10)
        response.raise_for_status()
        raw_m3u_content = response.text
    except Exception as e:
        print(f"❌ Error al descargar {filename} de origen: {e}")
        return filename, 0 

    lines = raw_m3u_content.split('\n')
    output_lines = ['#EXTM3U']
    valid_channels_count = 0
    validation_threads = []
    channels_to_validate = []

    # PASO 2: Filtrar (si se requiere) e identificar enlaces para validar
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF'):
            is_valid_language = True
            # APLICAR FILTRO DE IDIOMA SOLO SI apply_latin_filter es True (es decir, en cine.m3u)
            if apply_latin_filter:
                is_valid_language = is_latin_channel(line)
            
            if is_valid_language:
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

    # PASO 3: Ejecutar la validación multithreaded
    for line, url in channels_to_validate:
        thread = threading.Thread(target=lambda u: check_url_status(u), args=(url,))
        validation_threads.append(thread)
        thread.start()

    for thread in validation_threads:
        thread.join()

    # PASO 4: Construir la lista final usando el caché de estados
    for line, url in channels_to_validate:
        if url_status_cache.get(url, False):
            output_lines.append(line)
            output_lines.append(url)
            valid_channels_count += 1
            
    # Escribir el resultado
    save_m3u_content(filename, output_lines)
        
    print(f"✅ '{filename}' actualizado y limpiado. Canales válidos: {valid_channels_count}.")
    return filename, valid_channels_count

# --- GESTIÓN DEL HISTORIAL ---

def save_history(data):
    """Guarda el historial de canales en channels_history.json."""
    try:
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
    
    # 1. 🎬 PROCESAR LISTA CINE.M3U (REQUIERE FILTRO DE IDIOMA)
    filename, count = process_remote_list(MOVIES_SOURCE_URL, CINE_FILENAME, apply_latin_filter=True)
    new_channels_data[filename] = count
    
    # 2. 🌍 PROCESAR LISTAS DE PAÍSES (REQUIERE ACTUALIZACIÓN REMOTA Y LIMPIEZA, SIN FILTRO DE IDIOMA)
    # Invertimos el diccionario para iterar (URL -> Filename)
    for source_url, filename in COUNTRY_SOURCES.items():
        # Llama a la función, pero apply_latin_filter es False
        filename, count = process_remote_list(source_url, filename, apply_latin_filter=False)
        new_channels_data[filename] = count

    # 3. 💾 GUARDAR EL NUEVO HISTORIAL
    save_history(new_channels_data)
    
    print("\nProceso de validación de listas terminado.")

if __name__ == "__main__":
    main()
