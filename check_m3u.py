#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador de canales IPTV - OPTIMIZADO
- Timeouts cortos (3 segundos)
- Sin warnings de SSL
- Procesamiento en paralelo eficiente
"""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import warnings
import urllib3
from datetime import datetime

# ============================================
# CONFIGURACIÓN OPTIMIZADA
# ============================================

# Silenciar warnings de SSL (para no llenar el log)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

CONFIG = {
    'timeout': 3,           # Timeout por canal (3 segundos)
    'max_workers': 30,      # Hilos paralelos (aumentado)
    'max_retries': 1,       # Solo 1 reintento
    'verify_ssl': False     # Deshabilitar verificación SSL
}

# ============================================
# FUNCIONES CORE
# ============================================

def leer_m3u(archivo):
    """Lee un archivo M3U y extrae canales"""
    canales = []
    try:
        with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
            lineas = f.readlines()
            
        nombre_canal = None
        for linea in lineas:
            linea = linea.strip()
            
            if linea.startswith('#EXTINF'):
                # Extraer nombre del canal
                if ',' in linea:
                    nombre_canal = linea.split(',', 1)[1].strip()
                else:
                    nombre_canal = "Canal sin nombre"
            
            elif linea and not linea.startswith('#'):
                # Es una URL
                if nombre_canal:
                    canales.append({
                        'nombre': nombre_canal,
                        'url': linea,
                        'archivo': archivo.name
                    })
                nombre_canal = None
    
    except Exception as e:
        print(f"❌ Error leyendo {archivo}: {e}")
    
    return canales

def validar_canal(canal):
    """
    Valida un canal usando HEAD request con timeout corto
    Retorna el canal si es válido, None si falla
    """
    url = canal['url']
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # Intentar HEAD primero (más rápido)
        response = requests.head(
            url,
            headers=headers,
            timeout=CONFIG['timeout'],
            verify=CONFIG['verify_ssl'],
            allow_redirects=True
        )
        
        # Si HEAD no funciona, probar GET
        if response.status_code >= 400:
            response = requests.get(
                url,
                headers=headers,
                timeout=CONFIG['timeout'],
                verify=CONFIG['verify_ssl'],
                stream=True
            )
            response.close()
        
        # Canal válido si código < 400
        if response.status_code < 400:
            return canal
        
        return None
        
    except requests.exceptions.Timeout:
        # Timeout = canal lento o muerto
        return None
    except requests.exceptions.SSLError:
        # Error SSL = canal problemático
        return None
    except Exception:
        # Cualquier otro error = canal muerto
        return None

def validar_canales_paralelo(canales):
    """Valida canales en paralelo con progreso"""
    print(f"\n🔍 Validando {len(canales)} canales...")
    print(f"⚙️  Configuración: {CONFIG['max_workers']} hilos, timeout {CONFIG['timeout']}s")
    print("=" * 60)
    
    canales_validos = []
    procesados = 0
    
    with ThreadPoolExecutor(max_workers=CONFIG['max_workers']) as executor:
        futuros = {executor.submit(validar_canal, canal): canal for canal in canales}
        
        for futuro in as_completed(futuros):
            procesados += 1
            resultado = futuro.result()
            
            if resultado:
                canales_validos.append(resultado)
                # Mostrar progreso cada 50 canales
                if procesados % 50 == 0:
                    porcentaje = (procesados / len(canales)) * 100
                    print(f"✓ Procesados: {procesados}/{len(canales)} ({porcentaje:.1f}%) - Válidos: {len(canales_validos)}")
    
    print("=" * 60)
    print(f"✅ Validación completada:")
    print(f"   📊 Total: {len(canales)} canales")
    print(f"   ✓ Válidos: {len(canales_validos)}")
    print(f"   ✗ Caídos: {len(canales) - len(canales_validos)}")
    
    return canales_validos

def escribir_m3u(archivo, canales):
    """Escribe canales validados en formato M3U"""
    try:
        with open(archivo, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:Actualizado {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            
            for canal in canales:
                f.write(f"#EXTINF:-1,{canal['nombre']}\n")
                f.write(f"{canal['url']}\n")
        
        return True
    except Exception as e:
        print(f"❌ Error escribiendo {archivo}: {e}")
        return False

def procesar_archivo_m3u(archivo_path):
    """Procesa un archivo M3U completo"""
    print(f"\n{'=' * 60}")
    print(f"📄 Procesando: {archivo_path.name}")
    print(f"{'=' * 60}")
    
    # 1. Leer canales
    canales_originales = leer_m3u(archivo_path)
    print(f"📊 Canales encontrados: {len(canales_originales)}")
    
    if not canales_originales:
        print("⚠️  No hay canales para validar")
        return
    
    # 2. Validar canales
    canales_validos = validar_canales_paralelo(canales_originales)
    
    # 3. Guardar solo los válidos
    if canales_validos:
        if escribir_m3u(archivo_path, canales_validos):
            print(f"💾 Guardado: {archivo_path.name}")
            tasa_exito = (len(canales_validos) / len(canales_originales)) * 100
            print(f"📈 Tasa de éxito: {tasa_exito:.1f}%")
    else:
        print("⚠️  No hay canales válidos para guardar")

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("🚀 VERIFICADOR DE CANALES IPTV - MODO OPTIMIZADO")
    print("=" * 60)
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Buscar todos los archivos M3U
    archivos_m3u = list(Path('.').glob('*.m3u'))
    
    # Excluir archivos de respaldo si existen
    archivos_m3u = [f for f in archivos_m3u if not f.name.endswith('.backup.m3u')]
    
    if not archivos_m3u:
        print("❌ No se encontraron archivos M3U")
        return
    
    print(f"📁 Archivos encontrados: {len(archivos_m3u)}")
    for archivo in sorted(archivos_m3u):
        print(f"   • {archivo.name}")
    
    # Procesar cada archivo
    inicio = datetime.now()
    
    for archivo in sorted(archivos_m3u):
        procesar_archivo_m3u(archivo)
    
    # Resumen final
    duracion = (datetime.now() - inicio).total_seconds()
    
    print("\n" + "=" * 60)
    print("✨ PROCESO COMPLETADO")
    print("=" * 60)
    print(f"⏱️  Duración total: {duracion:.1f} segundos")
    print(f"⏰ Finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
