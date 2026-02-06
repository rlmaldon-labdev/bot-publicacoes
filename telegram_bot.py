"""
Módulo para notificações via Telegram
Envia alertas sobre novas publicações processadas
Versão Opus
"""

import requests
from datetime import datetime


class TelegramNotifier:
    def __init__(self, config):
        """Inicializa notificador do Telegram"""
        self.token = config.get('token', '')
        self.chat_id = config.get('chat_id', '')
        
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
        # Testa conexão se configurado
        if self.token and self.chat_id:
            self._testar_conexao()
        else:
            print("   ⚠️ Telegram não configurado (token ou chat_id vazio)")
    
    def _testar_conexao(self):
        """Testa se o bot do Telegram está acessível"""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    bot_name = bot_info.get('result', {}).get('username', 'desconhecido')
                    print(f"   ✅ Telegram conectado - Bot: @{bot_name}")
                    return True
            print(f"   ⚠️ Telegram: resposta inesperada")
            return False
        except Exception as e:
            print(f"   ⚠️ Telegram: erro ao conectar - {e}")
            return False
    
    def enviar_mensagem(self, mensagem):
        """Envia mensagem para o chat configurado"""
        if not self.token or not self.chat_id:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': mensagem,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, data=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"⚠️ Erro ao enviar mensagem Telegram: {e}")
            return False
    
    def notificar_processamento(self, dados, card_url):
        """Envia notificação sobre publicação processada"""
        
        # Monta mensagem com estética melhorada
        processo = dados.get('numero_processo') or 'Não identificado'
        cliente = dados.get('cliente') or 'Não identificado'
        tipo = dados.get('tipo_ato') or 'Não identificado'
        tribunal = dados.get('tribunal') or ''
        prazo = dados.get('prazo_calculado') or 'Não calculado'
        
        # Limita tamanho do cliente
        if len(str(cliente)) > 45:
            cliente = str(cliente)[:45] + '...'
        
        # Monta linha de urgência/prazo implícito
        avisos = ""
        if dados.get('urgente'):
            avisos += "\n⚡ <b>URGENTE!</b>"
        if dados.get('prazo_implicito'):
            avisos += "\n\n⚠️ <b>Prazo implícito (revisar!)</b>"
        
        mensagem = f"""🤖 <b>Nova Publicação Processada!</b>
━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Processo:</b> {processo}
👤 <b>Cliente:</b> {cliente}
🏷️ <b>Tipo:</b> {tipo}
🏛️ <b>Tribunal:</b> {tribunal}
📅 <b>Prazo:</b> {prazo}{avisos}
━━━━━━━━━━━━━━━━━━━━━━
🔗 <a href="{card_url}">Ver card no Trello</a>"""
        
        return self.enviar_mensagem(mensagem)
    
    def enviar_resumo_diario(self, sucesso, falhas, ignorados=0):
        """Envia resumo do processamento"""
        
        total = sucesso + falhas + ignorados
        hora = datetime.now().strftime("%H:%M")
        data = datetime.now().strftime("%d/%m/%Y")
        
        if total == 0:
            mensagem = f"""📊 <b>RESUMO - {data} {hora}</b>

📭 Nenhuma publicação nova encontrada."""
        else:
            taxa = (sucesso / total * 100) if total > 0 else 0
            
            ignorados_texto = f"\n⏭️ <b>Ignorados (lista especial):</b> {ignorados}" if ignorados > 0 else ""
            mensagem = f"""📊 <b>RESUMO - {data} {hora}</b>

📬 <b>Total processado:</b> {total} publicação(ões)
✅ <b>Cards criados:</b> {sucesso}{ignorados_texto}
❌ <b>Falhas:</b> {falhas}
📈 <b>Taxa de sucesso:</b> {taxa:.0f}%"""
        
        return self.enviar_mensagem(mensagem)
    
    def notificar_erro(self, erro):
        """Envia notificação de erro crítico"""
        
        mensagem = f"""🚨 <b>ERRO NO BOT DE PUBLICAÇÕES</b>

❌ <b>Erro:</b> {str(erro)[:500]}

⏰ <b>Horário:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}

<i>Verifique os logs para mais detalhes.</i>"""
        
        return self.enviar_mensagem(mensagem)
