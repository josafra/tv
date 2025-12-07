import requests
import re
import os
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- Configuración ---
TIMEOUT = 10
MAX_WORKERS = 20

# Archivo para guardar el estado anterior (historial)
HISTORY_FILE = 'channels_history.json'

MAPPING_FILES = {
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
    'https://iptv-org.github.io/iptv/categories/movies.m3u': 'cine.m3u',
}


def get_m3u_content(source):
    """Obtiene el contenido M3U de una URL externa."""
    print(f"🌐 Descargando contenido de: {source}")
    try:
        response = requests.get(source, timeout=TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al descargar {source}: {e}")
        return None


def parse_m3u(content):
    """Analiza la cadena de texto M3U y devuelve una lista de tuplas (nombre, url, extinf)."""
    channels = []
    matches = re.findall(r'(#EXTINF:.*?,(.*?)\n(.*?)\s*?)(?=\n#EXTINF|\Z)', content, re.DOTALL)

    for match in matches:
        url = match[2].strip()
        name = match[1].strip()
        
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
    
    # Método 1: HEAD Request
    try:
        response = requests.head(url, timeout=TIMEOUT, allow_redirects=True, verify=False)
        if 200 <= response.status_code < 400:
            channel['active'] = True
            print(f"  [ACTIVO - HEAD] {channel['name']}")
            return channel
    except requests.exceptions.RequestException:
        pass 

    # Método 2: GET parcial
    try:
        headers = {'Range': 'bytes=0-1024', 'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=TIMEOUT, headers=headers, allow_redirects=True, verify=False)
        
        if 200 <= response.status_code < 400:
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


def update_m3u_file(file_path, channels):
    """Genera un nuevo archivo M3U solo con los canales activos."""
    output_file = file_path 
    active_channels = [c for c in channels if c['active']]
    
    content = "#EXTM3U\n"
    for channel in active_channels:
        content += f"{channel['extinf']}\n{channel['url']}\n"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"✅ Lista limpia generada: {len(active_channels)} canales activos guardados en {output_file}")
    return active_channels


def load_history():
    """Carga el historial de canales del archivo JSON."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_history(history):
    """Guarda el historial de canales en un archivo JSON."""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def compare_channels(old_channels, new_channels, country_name):
    """Compara los canales antiguos con los nuevos y devuelve un resumen de cambios."""
    old_names = set(ch['name'] for ch in old_channels)
    new_names = set(ch['name'] for ch in new_channels)
    
    added = new_names - old_names
    removed = old_names - new_names
    
    return {
        'country': country_name,
        'total_old': len(old_channels),
        'total_new': len(new_channels),
        'added': sorted(list(added)),
        'removed': sorted(list(removed)),
        'unchanged': len(old_names & new_names)
    }


def generate_telegram_report(all_changes):
    """Genera el mensaje para Telegram con todos los cambios."""
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    report = f"📡 **ACTUALIZACIÓN IPTV** - {timestamp}\n"
    report += "=" * 40 + "\n\n"
    
    has_changes = False
    
    for change in all_changes:
        if change['added'] or change['removed']:
            has_changes = True
            report += f"🌍 **{change['country'].upper()}**\n"
            report += f"   Total canales: {change['total_new']}"
            
            if change['total_new'] > change['total_old']:
                report += f" (📈 +{change['total_new'] - change['total_old']})"
            elif change['total_new'] < change['total_old']:
                report += f" (📉 {change['total_new'] - change['total_old']})"
            
            report += "\n"
            
            if change['added']:
                report += f"   ✅ **Nuevos ({len(change['added'])})**:\n"
                for ch in change['added'][:10]:  # Limitar a 10 para no saturar
                    report += f"      • {ch}\n"
                if len(change['added']) > 10:
                    report += f"      ... y {len(change['added']) - 10} más\n"
            
            if change['removed']:
                report += f"   ❌ **Eliminados ({len(change['removed'])})**:\n"
                for ch in change['removed'][:5]:  # Limitar a 5
                    report += f"      • {ch}\n"
                if len(change['removed']) > 5:
                    report += f"      ... y {len(change['removed']) - 5} más\n"
            
            report += "\n"
    
    if not has_changes:
        report += "✅ **No hay cambios** - Todas las listas permanecen igual\n"
    
    # Guardar reporte en archivo
    with open('telegram_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    return report


def main():
    print("Iniciando proceso de verificación masiva de archivos M3U...")
    
    # Cargar historial
    history = load_history()
    all_changes = []

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

        # Paso 3: Verificar Canales en paralelo
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = list(executor.map(check_url_aggressive, channels))
            
        # Paso 4: Sobrescribir el archivo local
        active_channels = update_m3u_file(output_file_name, results)
        
        # Paso 5: Comparar con historial
        country_name = output_file_name.replace('.m3u', '').capitalize()
        old_channels = history.get(output_file_name, [])
        
        changes = compare_channels(old_channels, active_channels, country_name)
        all_changes.append(changes)
        
        # Actualizar historial
        history[output_file_name] = active_channels

    # Guardar nuevo historial
    save_history(history)
    
    # Generar reporte para Telegram
    report = generate_telegram_report(all_changes)
    print("\n" + "=" * 50)
    print(report)
    print("=" * 50)

    print("\nProceso de automatización finalizado.")


if __name__ == "__main__":
    main()
