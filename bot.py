"""
BOT DE PROCESSAMENTO DE PUBLICAÇÕES JURÍDICAS
Versão: 3.0

Este bot processa automaticamente publicações jurídicas recebidas por email,
extrai informações usando IA (Ollama local ou Gemini API), e cria cards no Trello.

Funcionalidades:
- Suporte a Ollama (local) ou Gemini (API)
- Lista especial: ignora publicações de clientes específicos
- Separação de múltiplas publicações por email
- Título do card com PF (Prazo Fatal)
- Notificações via Telegram
"""

import json
import time
import sys
import os
import unicodedata
from datetime import datetime
from pathlib import Path

# Importa módulos do bot
from processar_email import EmailProcessor
from processar_llm import LLMProcessor
from trello_manager import TrelloManager
from telegram_bot import TelegramNotifier


class ListaEspecial:
    """Gerencia a lista de clientes especiais"""
    
    def __init__(self, config):
        self.nomes = []
        self.acao = config.get('acao', 'ignorar')
        
        arquivo = config.get('arquivo', 'lista_especial.txt')
        if os.path.exists(arquivo):
            with open(arquivo, 'r', encoding='utf-8') as f:
                for linha in f:
                    nome = linha.strip()
                    if nome and not nome.startswith('#'):
                        self.nomes.append(self._normalizar(nome))
            print(f"   ✅ Lista especial carregada: {len(self.nomes)} nomes")
        else:
            print(f"   ⚠️ Arquivo {arquivo} não encontrado (lista especial vazia)")
    
    def _normalizar(self, texto):
        """Remove acentos e converte para maiúsculas"""
        texto = texto.upper()
        texto = unicodedata.normalize('NFKD', texto)
        texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
        return texto
    
    def verificar(self, texto_publicacao):
        """Verifica se algum nome da lista está na publicação"""
        texto_norm = self._normalizar(texto_publicacao)
        
        for nome in self.nomes:
            if nome in texto_norm:
                return True, nome
        
        return False, None


class BotPublicacoes:
    def __init__(self, config_path='config.json'):
        """Inicializa o bot com as configurações"""
        print("🤖 Iniciando Bot de Publicações (Versão 3.0)...")
        print("="*60)
        
        # Carrega configurações
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Inicializa componentes
        print("\n📧 Conectando ao email...")
        self.email_processor = EmailProcessor(self.config['email'])
        
        # Detecta provedor de IA
        ia_config = self.config.get('ia', {})
        provedor = ia_config.get('provedor', 'ollama')
        print(f"\n🧠 Conectando à IA ({provedor.upper()})...")
        self.llm_processor = LLMProcessor(ia_config)
        
        print("\n📋 Conectando ao Trello...")
        self.trello_manager = TrelloManager(self.config['trello'])
        
        print("\n📱 Configurando Telegram...")
        self.telegram = TelegramNotifier(self.config['telegram'])
        
        # Carrega lista especial
        print("\n📋 Carregando lista especial...")
        self.lista_especial = ListaEspecial(self.config.get('lista_especial', {}))
        
        print("\n" + "="*60)
        print("✅ Bot inicializado com sucesso!")
        print(f"   🧠 Provedor de IA: {self.llm_processor.get_provedor_info()}")
        print("="*60 + "\n")
        
        # Controle de emails processados
        self.emails_processados = set()
        
        # Contadores
        self.ignorados_lista_especial = 0
    
    def processar_publicacao(self, pub_data):
        """Processa uma única publicação"""
        try:
            numero_pub = pub_data.get('numero_publicacao', 1)
            total_pub = pub_data.get('total_publicacoes', 1)
            
            print(f"\n{'─'*50}")
            print(f"📄 Processando publicação {numero_pub}/{total_pub}...")
            print(f"{'─'*50}")
            
            # VERIFICAÇÃO DA LISTA ESPECIAL
            esta_na_lista, nome_encontrado = self.lista_especial.verificar(pub_data['corpo'])
            
            if esta_na_lista:
                print(f"⏭️ IGNORANDO - Cliente na lista especial: {nome_encontrado}")
                self.ignorados_lista_especial += 1
                # Ainda marca o email como processado
                self.emails_processados.add(pub_data['id'])
                return True  # Retorna True pois foi processado (ignorado intencionalmente)
            
            # 1. Extrai dados com IA
            print(f"🧠 Analisando com IA ({self.llm_processor.get_provedor_info()})...")
            dados_extraidos = self.llm_processor.extrair_dados(pub_data['corpo'])
            
            if not dados_extraidos:
                print("❌ Erro ao processar com IA")
                return False
            
            # Mostra dados extraídos
            print(f"✅ Dados extraídos:")
            print(f"   • Processo: {dados_extraidos.get('numero_processo') or 'N/A'}")
            cliente = dados_extraidos.get('cliente') or 'N/A'
            print(f"   • Cliente: {str(cliente)[:40]}...")
            print(f"   • Tipo: {dados_extraidos.get('tipo_ato') or 'N/A'}")
            print(f"   • Prazo (PF): {dados_extraidos.get('prazo_calculado') or 'N/A'}")
            print(f"   • Confiança: {int(dados_extraidos.get('confianca', 0) * 100)}%")
            
            # 2. Cria card no Trello
            print("\n📋 Criando card no Trello...")
            card = self.trello_manager.criar_card(dados_extraidos, pub_data)
            
            if card:
                print(f"✅ Card criado: {card['titulo'][:60]}...")
                print(f"   🔗 {card['url']}")
                
                # 3. Notifica no Telegram
                print("\n📱 Enviando notificação...")
                if self.telegram.notificar_processamento(dados_extraidos, card['url']):
                    print("✅ Notificação enviada!")
                else:
                    print("⚠️ Notificação não enviada")
                
                self.emails_processados.add(pub_data['id'])
                return True
            else:
                print("❌ Erro ao criar card")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao processar publicação: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def executar_uma_vez(self):
        """Processa todos os emails pendentes uma vez"""
        print("\n" + "="*60)
        print("🔍 VERIFICANDO EMAILS NOVOS...")
        print("="*60)
        
        # Reset contadores
        self.ignorados_lista_especial = 0
        
        # Busca emails
        publicacoes = self.email_processor.buscar_emails_novos(
            dias=self.config['processamento'].get('dias_verificar', 7)
        )
        
        if not publicacoes:
            print("\n📭 Nenhuma publicação nova encontrada.")
            return
        
        print(f"\n📬 {len(publicacoes)} publicação(ões) encontrada(s)!")
        
        # Processa cada publicação
        sucesso = 0
        falhas = 0
        
        for i, pub_data in enumerate(publicacoes, 1):
            print(f"\n{'='*60}")
            print(f"Processando {i}/{len(publicacoes)}")
            print(f"{'='*60}")
            
            if self.processar_publicacao(pub_data):
                sucesso += 1
            else:
                falhas += 1
            
            if i < len(publicacoes):
                print("\n⏳ Aguardando 3 segundos...")
                time.sleep(3)
        
        # Marca emails como lidos
        if self.config['email'].get('marcar_como_lido_apos_processar', True):
            print(f"\n📧 Marcando {len(self.emails_processados)} email(s) como lido(s)...")
            for email_id in self.emails_processados:
                try:
                    self.email_processor.marcar_email_como_lido(email_id)
                except Exception as e:
                    print(f"⚠️ Erro ao marcar email {email_id}: {e}")
            self.emails_processados.clear()
        
        # Resumo final
        cards_criados = sucesso - self.ignorados_lista_especial
        
        print(f"\n{'='*60}")
        print(f"📊 RESUMO DO PROCESSAMENTO")
        print(f"{'='*60}")
        print(f"📬 Total de publicações: {len(publicacoes)}")
        print(f"✅ Cards criados: {cards_criados}")
        print(f"⏭️ Ignorados (lista especial): {self.ignorados_lista_especial}")
        print(f"❌ Falhas: {falhas}")
        print(f"{'='*60}\n")
        
        # Envia resumo no Telegram
        self.telegram.enviar_resumo_diario(cards_criados, falhas, self.ignorados_lista_especial)
    
    def executar_continuo(self):
        """Executa continuamente"""
        intervalo = self.config['processamento'].get('intervalo_minutos', 15)
        
        print(f"\n{'='*60}")
        print(f"🔄 MODO CONTÍNUO ATIVADO")
        print(f"{'='*60}")
        print(f"⏱️  Intervalo: {intervalo} minutos")
        print(f"⌨️  Pressione Ctrl+C para parar")
        print(f"{'='*60}\n")
        
        try:
            while True:
                hora_atual = datetime.now().strftime("%H:%M:%S")
                print(f"\n⏰ [{hora_atual}] Iniciando verificação...")
                
                try:
                    self.executar_uma_vez()
                except Exception as e:
                    print(f"❌ Erro durante execução: {e}")
                    self.telegram.notificar_erro(e)
                
                from datetime import timedelta
                proxima = datetime.now() + timedelta(minutes=intervalo)
                
                print(f"\n💤 Aguardando {intervalo} minutos...")
                print(f"    Próxima verificação: {proxima.strftime('%H:%M:%S')}")
                
                time.sleep(intervalo * 60)
                
        except KeyboardInterrupt:
            print("\n\n⛔ Bot interrompido pelo usuário.")
            print("👋 Até logo!\n")


def main():
    """Função principal"""
    print("\n" + "="*60)
    print("🤖 BOT DE PUBLICAÇÕES JURÍDICAS")
    print("    Versão 3.0")
    print("="*60 + "\n")
    
    if not Path('config.json').exists():
        print("❌ Arquivo config.json não encontrado!")
        print("\nCampos necessários:")
        print("  - email: servidor, porta, usuario, senha, label")
        print("  - ia: provedor ('ollama' ou 'gemini'), ollama, gemini")
        print("  - trello: api_key, token, board_id, lista_id")
        print("  - telegram: token, chat_id")
        print("  - lista_especial: arquivo")
        input("\nPressione ENTER para sair...")
        sys.exit(1)
    
    try:
        bot = BotPublicacoes()
    except Exception as e:
        print(f"❌ Erro ao inicializar bot: {e}")
        import traceback
        traceback.print_exc()
        input("\nPressione ENTER para sair...")
        sys.exit(1)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--continuo':
        bot.executar_continuo()
    else:
        bot.executar_uma_vez()
        input("\n✅ Processamento concluído! Pressione ENTER para sair...")


if __name__ == "__main__":
    main()
