#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notificador de cambios en listas IPTV vía Telegram
Compatible con el workflow update-iptv.yml
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
    """Carga el historial previo de canales"""
    if Path(HISTORY_FILE).exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def guardar_historial(historial):
    """Guarda el historial actualizado"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(historial, f, indent=2, ensure_ascii=False)

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
            print(f"Error leyendo {archivo}: {e}")
            canales[archivo.name] = 0
    return canales

def generar_reporte(canales_actuales, historial_previo):
    """Genera reporte de cambios"""
    cambios = []
    total_actual = sum(canales_actuales.values())
    total_previo = sum(historial_previo.values()) if historial_previo else 0
    diferencia = total_actual - total_previo
    
    # Header
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
        for archivo, count_actual in sorted(canales_actuales.items()):
            count_previo = historial_previo.get(archivo, 0)
            diff = count_actual - count_previo
            
            if diff > 0:
                emoji = "🟢"
                texto = f"+{diff}"
            elif diff < 0:
                emoji = "🔴"
                texto = str(diff)
            else:
                emoji = "⚪"
                texto = "="
            
            reporte += f"{emoji} `{archivo}`: {count_actual} ({texto})\n"
    else:
        reporte += "📋 *ARCHIVOS M3U*\n"
        for archivo, count in sorted(canales_actuales.items()):
            reporte += f"• `{archivo}`: {count} canales\n"
    
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
        return False

def guardar_reporte_local(reporte):
    """Guarda el reporte en un archivo de texto"""
    with open('telegram_report.txt', 'w', encoding='utf-8') as f:
        # Limpiar formato Markdown para el archivo de texto
        reporte_limpio = reporte.replace('*', '').replace('`', '')
        f.write(reporte_limpio)
    print("💾 Reporte guardado en telegram_report.txt")

def main():
    print("=" * 50)
    print("📱 NOTIFICADOR DE CAMBIOS IPTV - TELEGRAM")
    print("=" * 50)
    
    # 1. Cargar historial previo
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
    
    # 6. Actualizar historial
    guardar_historial(canales_actuales)
    print("💾 Historial actualizado")
    
    print("\n✨ Proceso completado")

if __name__ == "__main__":
    main()
