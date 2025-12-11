#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notificador de cambios en listas IPTV vía Telegram
Compatible con el workflow update-iptv.yml
VERSIÓN MEJORADA: Envía dos reportes diferenciados
  1. Reporte de actualización (canales nuevos desde fuentes remotas)
  2. Reporte de limpieza (canales eliminados de archivos locales)
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
CLEANING_HISTORY_FILE = 'cleaning_history.json'

def cargar_historial(filepath):
    """Carga un historial desde archivo JSON (con manejo de errores)"""
    if not Path(filepath).exists():
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        
        # Validar que los valores sean números o diccionarios válidos
        historial_limpio = {}
        for key, value in historial.items():
            # Para historial de actualización (números simples)
            if isinstance(value, list):
                historial_limpio[key] = value[0] if value and isinstance(value[0], (int, float)) else 0
            elif isinstance(value, (int, float)):
                historial_limpio[key] = value
            # Para historial de limpieza (diccionarios con estadísticas)
            elif isinstance(value, dict):
                historial_limpio[key] = value
            else:
                historial_limpio[key] = 0
        
        return historial_limpio
    
    except Exception as e:
        print(f"⚠️  Error cargando {filepath}: {e}")
        return {}

def guardar_historial(filepath, historial):
    """Guarda el historial actualizado"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(historial, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error guardando {filepath}: {e}")
        return False

# ========================================
# REPORTE 1: ACTUALIZACIÓN (canales nuevos)
# ========================================

def generar_reporte_actualizacion(canales_actuales, historial_previo):
    """Genera reporte de canales nuevos desde fuentes remotas"""
    total_actual = sum(canales_actuales.values())
    total_previo = sum(historial_previo.values()) if historial_previo else 0
    diferencia = total_actual - total_previo
    
    # Header con fecha correcta
    reporte = f"📺 *REPORTE IPTV - ACTUALIZACIÓN*\n"
    reporte += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    reporte += f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    
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
            for linea in cambios_importantes[:10]:
                reporte += linea + "\n"
            
            if len(cambios_importantes) > 10:
                reporte += f"... y {len(cambios_importantes) - 10} más con cambios\n"
        
        # Resumen de archivos sin cambios
        if sin_cambios:
            reporte += f"\n⚪ {len(sin_cambios)} listas sin cambios\n"
    
    else:
        reporte += "📋 *PRIMERA EJECUCIÓN*\n"
        reporte += f"• Total archivos: {len(canales_actuales)}\n"
        reporte += f"• Total canales: {total_actual}\n"
    
    reporte += "\n━━━━━━━━━━━━━━━━━━━━━\n"
    reporte += "🤖 Actualización automática"
    
    return reporte

# ========================================
# REPORTE 2: LIMPIEZA (canales eliminados)
# ========================================

def generar_reporte_limpieza(cleaning_results):
    """Genera reporte de limpieza de canales muertos"""
    
    # Calcular totales
    total_archivos = len(cleaning_results)
    total_before = sum(r.get('before', 0) for r in cleaning_results.values())
    total_after = sum(r.get('after', 0) for r in cleaning_results.values())
    total_removed = sum(r.get('removed', 0) for r in cleaning_results.values())
    
    # Header
    reporte = f"🧹 *REPORTE IPTV - LIMPIEZA LOCAL*\n"
    reporte += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    reporte += f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    
    # Resumen general
    reporte += f"🔍 *VERIFICACIÓN DE CANALES*\n"
    reporte += f"• Total archivos: *{total_archivos}*\n"
    reporte += f"• Canales verificados: *{total_before}*\n"
    
    if total_removed > 0:
        reporte += f"• 🔴 *{total_removed} canales eliminados* (muertos)\n"
        reporte += f"• ✅ {total_after} canales vivos\n"
    else:
        reporte += f"• ✅ *Todos los canales están vivos*\n"
        reporte += f"• Total vivos: {total_after}\n"
    
    reporte += "\n"
    
    # Detalles por archivo (solo los que tuvieron cambios)
    archivos_con_cambios = []
    archivos_sin_cambios = []
    
    for archivo, stats in sorted(cleaning_results.items()):
        removed = stats.get('removed', 0)
        before = stats.get('before', 0)
        after = stats.get('after', 0)
        
        if removed > 0:
            archivos_con_cambios.append(f"🔴 `{archivo}`: -{removed} canales ({after} vivos)")
        else:
            archivos_sin_cambios.append(archivo)
    
    if archivos_con_cambios:
        reporte += "📋 *CANALES ELIMINADOS POR LISTA*\n"
        
        # Mostrar máximo 15 archivos con cambios
        for linea in archivos_con_cambios[:15]:
            reporte += linea + "\n"
        
        if len(archivos_con_cambios) > 15:
            reporte += f"... y {len(archivos_con_cambios) - 15} archivos más con cambios\n"
    
    if archivos_sin_cambios:
        reporte += f"\n✅ {len(archivos_sin_cambios)} listas sin canales muertos\n"
    
    reporte += "\n━━━━━━━━━━━━━━━━━━━━━\n"
    reporte += "🤖 Verificación automática"
    
    return reporte

# ========================================
# FUNCIÓN DE ENVÍO A TELEGRAM
# ========================================

def enviar_telegram(mensaje, tipo="info"):
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
        print(f"✅ Reporte de {tipo} enviado a Telegram")
        return True
    except Exception as e:
        print(f"❌ Error enviando reporte de {tipo} a Telegram: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Respuesta: {e.response.text}")
        return False

def guardar_reporte_local(reporte, filename):
    """Guarda el reporte en un archivo de texto"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # Limpiar formato Markdown para el archivo de texto
            reporte_limpio = reporte.replace('*', '').replace('`', '')
            f.write(reporte_limpio)
        print(f"💾 Reporte guardado en {filename}")
        return True
    except Exception as e:
        print(f"❌ Error guardando {filename}: {e}")
        return False

# ========================================
# FUNCIÓN PRINCIPAL
# ========================================

def main():
    print("=" * 60)
    print("📱 NOTIFICADOR DE CAMBIOS IPTV - TELEGRAM")
    print("=" * 60)
    
    reportes_enviados = 0
    
    # ========================================
    # REPORTE 1: ACTUALIZACIÓN (si existe)
    # ========================================
    
    if Path(HISTORY_FILE).exists():
        print("\n📺 Procesando reporte de ACTUALIZACIÓN...")
        
        # Cargar historial actual (recién generado por check_m3u.py)
        canales_actuales = cargar_historial(HISTORY_FILE)
        
        # Intentar cargar historial previo (si existe backup)
        historial_previo_file = HISTORY_FILE + '.old'
        if Path(historial_previo_file).exists():
            historial_previo = cargar_historial(historial_previo_file)
        else:
            # Primera ejecución, usar datos actuales como referencia
            historial_previo = {}
        
        # Generar y enviar reporte de actualización
        reporte_update = generar_reporte_actualizacion(canales_actuales, historial_previo)
        
        print("\n" + "=" * 60)
        print(reporte_update.replace('*', '').replace('`', ''))
        print("=" * 60)
        
        guardar_reporte_local(reporte_update, 'telegram_report_update.txt')
        
        if enviar_telegram(reporte_update, tipo="actualización"):
            reportes_enviados += 1
        
        # Guardar copia del historial actual para la próxima ejecución
        guardar_historial(historial_previo_file, canales_actuales)
    
    # ========================================
    # REPORTE 2: LIMPIEZA (si existe)
    # ========================================
    
    if Path(CLEANING_HISTORY_FILE).exists():
        print("\n🧹 Procesando reporte de LIMPIEZA...")
        
        cleaning_results = cargar_historial(CLEANING_HISTORY_FILE)
        
        if cleaning_results:
            # Generar y enviar reporte de limpieza
            reporte_cleaning = generar_reporte_limpieza(cleaning_results)
            
            print("\n" + "=" * 60)
            print(reporte_cleaning.replace('*', '').replace('`', ''))
            print("=" * 60)
            
            guardar_reporte_local(reporte_cleaning, 'telegram_report_cleaning.txt')
            
            if enviar_telegram(reporte_cleaning, tipo="limpieza"):
                reportes_enviados += 1
    
    # ========================================
    # RESUMEN FINAL
    # ========================================
    
    print("\n" + "=" * 60)
    if reportes_enviados > 0:
        print(f"✨ Proceso completado: {reportes_enviados} reporte(s) enviado(s)")
    else:
        print("⚠️  No se enviaron reportes (archivos de historial no encontrados)")
    print("=" * 60)

if __name__ == "__main__":
    main()
