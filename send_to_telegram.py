#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notificador de cambios en listas IPTV vía Telegram
Compatible con el workflow update-iptv.yml
VERSIÓN CORREGIDA: Maneja historial corrupto
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path

# Configuración desde variables de entorno
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
HISTORY_FILE = 'channels_history.json'

def cargar_historial():
    """Carga el historial previo de canales (con manejo de errores)"""
    if not Path(HISTORY_FILE).exists():
        return {}
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        
        # CORRECCIÓN: Validar que los valores sean números
        historial_limpio = {}
        for key, value in historial.items():
            # Si el valor es una lista, tomar el primer elemento
            if isinstance(value, list):
                historial_limpio[key] = value[0] if value and isinstance(value[0], (int, float)) else 0
            # Si es un número, usarlo directamente
            elif isinstance(value, (int, float)):
                historial_limpio[key] = value
            else:
                # Cualquier otra cosa, ignorar
                historial_limpio[key] = 0
        
        return historial_limpio
    
    except Exception as e:
        print(f"⚠️  Error cargando historial: {e}")
        print("   Se creará un historial nuevo")
        return {}

def guardar_historial(historial):
    """Guarda el historial actualizado"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error guardando historial: {e}")
        return False

def contar_canales_m3u():
    """Cuenta los canales en todos los archivos M3U"""
    canales = {}
    for archivo in Path('.').glob('*.m3u'):
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                # Contar líneas #EXTINF
                count = contenido.count('#EXTINF')
                canales[archivo.name] = count
        except Exception as e:
            print(f"⚠️  Error leyendo {archivo}: {e}")
            canales[archivo.name] = 0
    return canales

def generar_reporte(canales_actuales, historial_previo):
    """Genera reporte de cambios"""
    total_actual = sum(canales_actuales.values())
    total_previo = sum(historial_previo.values()) if historial_previo else 0
    diferencia = total_actual - total_previo
    
    # Header con fecha correcta
    reporte = f"📺 *REPORTE IPTV* - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    reporte += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Resumen general
    reporte += f"📊 *RESUMEN GENERAL*\n"
    reporte += f"• Total canales: *{total_actual}*\n"
    
    if diferencia > 0:
        reporte += f"• 🟢 +{diferencia} nuevos canales\n"
    elif diferencia < 0:
        reporte += f"• 🔴 {diferencia} canales caídos\n"
    else:
        reporte += f"• ⚪ Sin cambios\n"
    
    reporte += "\n"
    
    # Detalles por archivo
    if historial_previo:
        reporte += "📋 *DETALLES POR LISTA*\n"
        
        # Mostrar solo los archivos con cambios significativos
        cambios_importantes = []
        sin_cambios = []
        
        for archivo, count_actual in sorted(canales_actuales.items()):
            count_previo = historial_previo.get(archivo, 0)
            diff = count_actual - count_previo
            
            if diff != 0:
                if diff > 0:
                    emoji = "🟢"
                    texto = f"+{diff}"
                else:
                    emoji = "🔴"
                    texto = str(diff)
                
                cambios_importantes.append(f"{emoji} `{archivo}`: {count_actual} ({texto})")
            else:
                sin_cambios.append(archivo)
        
        # Mostrar archivos con cambios
        if cambios_importantes:
            for linea in cambios_importantes[:10]:  # Máximo 10 para no saturar
                reporte += linea + "\n"
            
            if len(cambios_importantes) > 10:
                reporte += f"... y {len(cambios_importantes) - 10} más con cambios\n"
        
        # Resumen de archivos sin cambios
        if sin_cambios:
            reporte += f"\n⚪ {len(sin_cambios)} listas sin cambios\n"
    
    else:
        # Primera ejecución, mostrar solo totales
        reporte += "📋 *PRIMERA EJECUCIÓN*\n"
        reporte += f"• Total archivos: {len(canales_actuales)}\n"
        reporte += f"• Total canales: {total_actual}\n"
    
    reporte += "\n━━━━━━━━━━━━━━━━━━━━━\n"
    reporte += "🤖 Actualización automática"
    
    return reporte

def enviar_telegram(mensaje):
    """Envía mensaje a Telegram"""
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️  Variables de Telegram no configuradas")
        print("   Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en GitHub Secrets")
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': CHAT_ID,
        'text': mensaje,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Notificación enviada a Telegram")
        return True
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Respuesta: {e.response.text}")
        return False

def guardar_reporte_local(reporte):
    """Guarda el reporte en un archivo de texto"""
    try:
        with open('telegram_report.txt', 'w', encoding='utf-8') as f:
            # Limpiar formato Markdown para el archivo de texto
            reporte_limpio = reporte.replace('*', '').replace('`', '')
            f.write(reporte_limpio)
        print("💾 Reporte guardado en telegram_report.txt")
        return True
    except Exception as e:
        print(f"❌ Error guardando reporte: {e}")
        return False

def main():
    print("=" * 50)
    print("📱 NOTIFICADOR DE CAMBIOS IPTV - TELEGRAM")
    print("=" * 50)
    
    # 1. Cargar historial previo (con validación)
    historial_previo = cargar_historial()
    print(f"📂 Historial previo: {len(historial_previo)} archivos registrados")
    
    # 2. Contar canales actuales
    canales_actuales = contar_canales_m3u()
    print(f"📊 Archivos M3U encontrados: {len(canales_actuales)}")
    
    if not canales_actuales:
        print("⚠️  No se encontraron archivos M3U")
        return
    
    # 3. Generar reporte
    reporte = generar_reporte(canales_actuales, historial_previo)
    print("\n" + "=" * 50)
    print(reporte.replace('*', '').replace('`', ''))
    print("=" * 50 + "\n")
    
    # 4. Guardar reporte local
    guardar_reporte_local(reporte)
    
    # 5. Enviar a Telegram
    enviar_telegram(reporte)
    
    # 6. Actualizar historial (guardar solo números)
    if guardar_historial(canales_actuales):
        print("💾 Historial actualizado correctamente")
    
    print("\n✨ Proceso completado")

if __name__ == "__main__":
    main()
