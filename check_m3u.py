import os
import requests
import json
import threading
from datetime import datetime
import urllib3

# Silenciar warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN Y CONSTANTES ---

# 📌 Fuentes Remotas de IPTV-ORG para la actualización de listas de países
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

# 📌 Palabras clave MEJORADAS para el filtrado de idioma
LATIN_KEYWORDS = [
    # Idioma explícito
    'español', 'espanol', 'castellano', 'spanish', 'spa', 'esp',
    
    # Países hispanohablantes
    'spain', 'españa', 'mexico', 'méxico', 'argentina', 'colombia',
    'chile', 'peru', 'perú', 'venezuela', 'ecuador', 'bolivia',
    'paraguay', 'uruguay', 'guatemala', 'honduras', 'nicaragua',
    'costa rica', 'panama', 'panamá', 'el salvador', 'cuba',
    'puerto rico', 'dominicana', 'república dominicana',
    
    # Indicadores latinos
    'latino', 'latina', 'latam', 'latinoamericano', 'latinoamerica',
    'hispano', 'hispana', 'iberoamericano', 'habla hispana',
]

# Palabras que EXCLUYEN el canal (no es español)
EXCLUDE_KEYWORDS = [
    'english', 'french', 'german', 'italian', 'portuguese',
    'hindi', 'arabic', 'chinese', 'japanese', 'korean',
    'inglés', 'ingles', 'francés', 'frances', 'alemán', 'aleman',
    'usa', 'uk', 'united states', 'united kingdom',
    'brazil', 'brasil', 'france', 'germany', 'italy',
    ' en ', ' eng ', '[en]', '[eng]', '(en)', '(eng)',
    'tvg-language="en"', 'tvg-language="fr"', 'tvg-language="de"',
]

TIMEOUT = 3
HISTORY_FILE = 'channels_history.json'

# Variables globales para el multithreading
url_status_cache = {}
lock = threading.Lock()

# --- FUNCIONES DE UTILIDAD Y VALIDACIÓN ---

def check_url_status(url):
    """
    Verifica el estado de una URL usando timeout de 3 segundos.
    Utiliza caché para no verificar la misma URL varias veces.
    """
    with lock:
        if url in url_status_cache:
            return url_status_cache[url]
    
    try:
        response = requests.head(
            url, 
            timeout=TIMEOUT, 
            allow_redirects=True,
            verify=False  # Evitar errores SSL
        )
        is_valid = response.status_code < 400
    except requests.exceptions.RequestException:
        is_valid = False
    
    with lock:
        url_status_cache[url] = is_valid
    return is_valid

def is_latin_channel(extinf_line, url_line):
    """
    FILTRO MEJORADO: Verifica si un canal es latino/español.
    Analiza tanto la línea #EXTINF como la URL.
    
    Retorna True si es español/latino, False si no lo es.
    """
    # Combinar ambas líneas para análisis completo
    full_text = (extinf_line + " " + url_line).lower()
    
    # PASO 1: Rechazar explícitamente si tiene palabras de exclusión
    for exclude_word in EXCLUDE_KEYWORDS:
        if exclude_word in full_text:
            return False
    
    # PASO 2: Aceptar si tiene palabras latinas/españolas
    for keyword in LATIN_KEYWORDS:
        if keyword in full_text:
            return True
    
    # PASO 3: Buscar atributos TVG específicos de países hispanohablantes
    spanish_countries = ['es', 'mx', 'ar', 'co', 'cl', 'pe', 've', 'ec', 
                         'uy', 'py', 'bo', 'cr', 'pa', 'gt', 'hn', 'sv', 
                         'ni', 'cu', 'pr', 'do']
    
    for country_code in spanish_countries:
        if f'tvg-country="{country_code}"' in full_text:
            return True
        if f'tvg-language="{country_code}"' in full_text:
            return True
    
    # PASO 4: Por defecto, RECHAZAR si no hay indicadores claros
    # (Modo estricto: solo acepta canales con marcadores explícitos)
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
    print(f"\n{'='*60}")
    print(f"📄 Procesando: {filename}")
    print(f"🔗 Fuente: {source_url}")
    if apply_latin_filter:
        print(f"🔍 Filtro de español: ACTIVADO")
    print(f"{'='*60}")
    
    # 1. DESCARGA EL CONTENIDO REMOTO
    try:
        response = requests.get(source_url, timeout=10, verify=False)
        response.raise_for_status()
        raw_m3u_content = response.text
    except Exception as e:
        print(f"❌ Error al descargar {filename}: {e}")
        return filename, 0

    lines = raw_m3u_content.split('\n')
    output_lines = ['#EXTM3U']
    valid_channels_count = 0
    validation_threads = []
    channels_to_validate = []
    
    total_found = 0
    filtered_out = 0

    # PASO 2: Filtrar e identificar canales
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF'):
            total_found += 1
            
            # Obtener la URL (siguiente línea)
            url = ""
            if i + 1 < len(lines):
                url = lines[i+1].strip()
            
            # APLICAR FILTRO DE IDIOMA SOLO PARA CINE
            passes_filter = True
            if apply_latin_filter:
                passes_filter = is_latin_channel(line, url)
                if not passes_filter:
                    filtered_out += 1
                    if filtered_out <= 5:  # Mostrar solo los primeros 5 ejemplos
                        channel_name = line.split(',')[-1] if ',' in line else "Sin nombre"
                        print(f"  ❌ Filtrado: {channel_name[:60]}")
            
            # Si pasa el filtro, añadir a la lista de validación
            if passes_filter and url:
                channels_to_validate.append((line, url))
                i += 2
            else:
                i += 2
        else:
            i += 1

    print(f"\n📊 Análisis inicial:")
    print(f"   • Total encontrados: {total_found}")
    if apply_latin_filter:
        print(f"   • Filtrados (no español): {filtered_out}")
        print(f"   • Pasaron filtro: {len(channels_to_validate)}")
    
    # PASO 3: Validar enlaces en paralelo
    print(f"\n🔍 Validando {len(channels_to_validate)} canales...")
    
    for line, url in channels_to_validate:
        thread = threading.Thread(target=lambda u: check_url_status(u), args=(url,))
        validation_threads.append(thread)
        thread.start()

    for thread in validation_threads:
        thread.join()

    # PASO 4: Construir la lista final
    for line, url in channels_to_validate:
        if url_status_cache.get(url, False):
            output_lines.append(line)
            output_lines.append(url)
            valid_channels_count += 1
    
    # Guardar resultado
    save_m3u_content(filename, output_lines)
    
    print(f"\n✅ Resultado final:")
    print(f"   • Canales válidos (vivos): {valid_channels_count}")
    print(f"   • Guardado en: {filename}")
    
    return filename, valid_channels_count

# --- GESTIÓN DEL HISTORIAL ---

def save_history(data):
    """Guarda el historial de canales en channels_history.json."""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print("\n💾 Historial actualizado correctamente")
    except Exception as e:
        print(f"❌ Error al guardar el historial: {e}")

# --- FLUJO PRINCIPAL ---

def main():
    global url_status_cache
    url_status_cache = {}
    new_channels_data = {}
    
    print("="*60)
    print("🚀 SISTEMA DE ACTUALIZACIÓN Y LIMPIEZA DE LISTAS IPTV")
    print("="*60)
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 1. 🎬 PROCESAR CINE.M3U (CON FILTRO DE ESPAÑOL/LATINO)
    print("\n🎬 PASO 1: Procesando lista de CINE (con filtro de español)")
    filename, count = process_remote_list(
        MOVIES_SOURCE_URL, 
        CINE_FILENAME, 
        apply_latin_filter=True  # ← FILTRO ACTIVADO
    )
    new_channels_data[filename] = count
    
    # 2. 🌍 PROCESAR LISTAS DE PAÍSES (SIN FILTRO)
    print("\n\n🌍 PASO 2: Procesando listas de países")
    for source_url, filename in COUNTRY_SOURCES.items():
        filename, count = process_remote_list(
            source_url, 
            filename, 
            apply_latin_filter=False  # ← SIN FILTRO
        )
        new_channels_data[filename] = count

    # 3. 💾 GUARDAR HISTORIAL
    save_history(new_channels_data)
    
    print("\n" + "="*60)
    print("✨ PROCESO COMPLETADO")
    print("="*60)
    print(f"⏰ Finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Total archivos procesados: {len(new_channels_data)}")
    print("="*60)

if __name__ == "__main__":
    main()
