import os
import requests

def send_telegram_message():
    """Envía el reporte de cambios al grupo de Telegram."""
    
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    if not TOKEN or not CHAT_ID:
        print("❌ Error: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están configurados")
        return False
    
    # Leer el reporte generado
    try:
        with open('telegram_report.txt', 'r', encoding='utf-8') as f:
            message = f.read()
    except FileNotFoundError:
        print("❌ Error: No se encontró el archivo telegram_report.txt")
        return False
    
    # Enviar mensaje a Telegram
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # Dividir mensaje si es muy largo (Telegram tiene límite de 4096 caracteres)
    max_length = 4000
    
    if len(message) <= max_length:
        # Enviar mensaje único
        payload = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            print("✅ Mensaje enviado exitosamente a Telegram")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al enviar mensaje: {e}")
            return False
    else:
        # Dividir mensaje en partes
        lines = message.split('\n')
        current_message = ""
        message_count = 1
        
        for line in lines:
            if len(current_message) + len(line) + 1 < max_length:
                current_message += line + '\n'
            else:
                # Enviar parte actual
                payload = {
                    'chat_id': CHAT_ID,
                    'text': f"📄 Parte {message_count}\n\n{current_message}",
                    'parse_mode': 'Markdown'
                }
                
                try:
                    response = requests.post(url, json=payload)
                    response.raise_for_status()
                    print(f"✅ Parte {message_count} enviada")
                except requests.exceptions.RequestException as e:
                    print(f"❌ Error al enviar parte {message_count}: {e}")
                    return False
                
                # Reiniciar para siguiente parte
                current_message = line + '\n'
                message_count += 1
        
        # Enviar última parte
        if current_message:
            payload = {
                'chat_id': CHAT_ID,
                'text': f"📄 Parte {message_count}\n\n{current_message}",
                'parse_mode': 'Markdown'
            }
            
            try:
                response = requests.post(url, json=payload)
                response.raise_for_status()
                print(f"✅ Parte {message_count} enviada (final)")
            except requests.exceptions.RequestException as e:
                print(f"❌ Error al enviar parte final: {e}")
                return False
        
        print(f"✅ Mensaje completo enviado en {message_count} partes")
        return True


if __name__ == "__main__":
    send_telegram_message()
