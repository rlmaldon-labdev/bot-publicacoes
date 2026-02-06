"""
Script para testar configuração do Bot de Publicações
Versão 3.0

Testa cada componente individualmente:
1. Conexão com Gmail (via label)
2. Conexão com IA (Ollama OU Gemini)
3. Conexão com Trello
4. Conexão com Telegram
5. Lista Especial
"""

import json
import sys
import os
from pathlib import Path


def cor(texto, codigo):
    """Adiciona cor ao texto (terminal)"""
    return f"\033[{codigo}m{texto}\033[0m"


def verde(texto):
    return cor(texto, '92')


def vermelho(texto):
    return cor(texto, '91')


def amarelo(texto):
    return cor(texto, '93')


def azul(texto):
    return cor(texto, '94')


def testar_email(config):
    """Testa conexão com email"""
    print(f"\n{azul('=' * 60)}")
    print(azul('📧 TESTANDO CONEXÃO COM EMAIL'))
    print(azul('=' * 60))
    
    try:
        from processar_email import EmailProcessor
        
        print(f"\n   Servidor: {config['servidor']}")
        print(f"   Usuário: {config['usuario']}")
        print(f"   Label: {config.get('label', 'INBOX')}")
        
        processor = EmailProcessor(config)
        processor._selecionar_label()
        
        print("\n   Buscando emails não lidos...")
        
        status, messages = processor.mail.search(None, 'UNSEEN')
        if status == 'OK':
            qtd = len(messages[0].split()) if messages[0] else 0
            print(f"   {verde('✅ Conexão OK - ' + str(qtd) + ' email(s) não lido(s)')}")
            
            if qtd > 0:
                print("\n   Testando processamento do primeiro email...")
                emails = processor.buscar_emails_novos(dias=7)
                if emails:
                    print(f"   {verde('✅ ' + str(len(emails)) + ' publicação(ões) identificada(s)')}")
        
        processor.desconectar()
        return True
        
    except Exception as e:
        print(f"\n   {vermelho('❌ ERRO: ' + str(e))}")
        return False


def testar_ia(config):
    """Testa conexão com IA (Ollama ou Gemini)"""
    print(f"\n{azul('=' * 60)}")
    print(azul('🧠 TESTANDO CONEXÃO COM IA'))
    print(azul('=' * 60))
    
    provedor = config.get('provedor', 'ollama').lower()
    print(f"\n   Provedor configurado: {provedor.upper()}")
    
    if provedor == 'gemini':
        return testar_gemini(config.get('gemini', {}))
    else:
        return testar_ollama(config.get('ollama', {}))


def testar_ollama(config):
    """Testa conexão com Ollama"""
    try:
        import requests
        
        url = config.get('url', 'http://localhost:11434')
        modelo = config.get('modelo', 'llama3.1:8b-instruct-q4_K_M')
        
        print(f"   URL: {url}")
        print(f"   Modelo: {modelo}")
        
        # Testa conexão
        response = requests.get(f"{url}/api/tags", timeout=10)
        
        if response.status_code == 200:
            modelos = response.json().get('models', [])
            modelo_base = modelo.split(':')[0]
            
            encontrado = False
            for m in modelos:
                nome_modelo = m.get('name', '')
                if modelo_base in nome_modelo:
                    encontrado = True
                    print(f"   {verde('✅ Modelo encontrado: ' + nome_modelo)}")
                    break
            
            if not encontrado:
                print(f"   {amarelo('⚠️ Modelo ' + modelo + ' não encontrado')}")
                print("   Modelos disponíveis:")
                for m in modelos:
                    print(f"      - {m.get('name')}")
                return False
            
            # Testa geração
            print("\n   Testando geração de texto...")
            
            test_response = requests.post(
                f"{url}/api/generate",
                json={
                    "model": modelo,
                    "prompt": "Responda apenas 'OK' se você estiver funcionando.",
                    "stream": False,
                    "options": {"num_predict": 10}
                },
                timeout=30
            )
            
            if test_response.status_code == 200:
                print(f"   {verde('✅ Ollama funcionando corretamente')}")
                return True
            else:
                print(f"   {vermelho('❌ Erro na geração: ' + str(test_response.status_code))}")
                return False
        else:
            print(f"   {vermelho('❌ Ollama não respondeu: ' + str(response.status_code))}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n   {vermelho('❌ Não foi possível conectar ao Ollama')}")
        print(f"   {amarelo('ℹ️  Certifique-se que o Ollama está rodando')}")
        print(f"   {amarelo('   Execute: ollama serve')}")
        return False
    except Exception as e:
        print(f"\n   {vermelho('❌ ERRO: ' + str(e))}")
        return False


def testar_gemini(config):
    """Testa conexão com Gemini API"""
    try:
        import requests
        
        api_key = config.get('api_key', '')
        modelo = config.get('modelo', 'gemini-2.5-flash')
        
        if not api_key:
            print(f"   {vermelho('❌ API Key do Gemini não configurada')}")
            return False
        
        api_key_preview = api_key[:10] + '...' if len(api_key) > 10 else api_key
        print(f"   API Key: {api_key_preview}")
        print(f"   Modelo: {modelo}")
        
        # Testa conexão
        print("\n   Testando conexão com Gemini...")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        
        response = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": "Responda apenas: OK"}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 10}
            },
            timeout=15
        )
        
        if response.status_code == 200:
            print(f"   {verde('✅ Gemini funcionando corretamente')}")
            return True
        elif response.status_code == 400:
            error = response.json().get('error', {}).get('message', 'Erro desconhecido')
            print(f"   {vermelho('❌ Erro na API: ' + error)}")
            return False
        elif response.status_code == 403:
            print(f"   {vermelho('❌ API Key inválida ou sem permissão')}")
            return False
        elif response.status_code == 404:
            print(f"   {vermelho('❌ Modelo não encontrado: ' + modelo)}")
            print(f"   {amarelo('ℹ️  Modelos disponíveis: gemini-2.5-flash, gemini-1.5-flash, gemini-1.5-pro')}")
            return False
        else:
            print(f"   {vermelho('❌ Erro: ' + str(response.status_code) + ' - ' + response.text[:100])}")
            return False
            
    except Exception as e:
        print(f"\n   {vermelho('❌ ERRO: ' + str(e))}")
        return False


def testar_trello(config):
    """Testa conexão com Trello"""
    print(f"\n{azul('=' * 60)}")
    print(azul('📋 TESTANDO CONEXÃO COM TRELLO'))
    print(azul('=' * 60))
    
    try:
        import requests
        
        api_key_preview = config['api_key'][:10] + '...' if len(config['api_key']) > 10 else config['api_key']
        print(f"\n   API Key: {api_key_preview}")
        print(f"   Board ID: {config.get('board_id', 'N/A')}")
        print(f"   Lista ID: {config['lista_id']}")
        
        base_url = "https://api.trello.com/1"
        params = {'key': config['api_key'], 'token': config['token']}
        
        if config.get('board_id'):
            response = requests.get(
                f"{base_url}/boards/{config['board_id']}",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                board = response.json()
                board_name = board.get('name', 'Sem nome')
                print(f"   {verde('✅ Board encontrado: ' + board_name)}")
            else:
                print(f"   {vermelho('❌ Board não encontrado: ' + str(response.status_code))}")
                return False
        
        response = requests.get(
            f"{base_url}/lists/{config['lista_id']}",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            lista = response.json()
            lista_name = lista.get('name', 'Sem nome')
            print(f"   {verde('✅ Lista encontrada: ' + lista_name)}")
            return True
        else:
            print(f"   {vermelho('❌ Lista não encontrada: ' + str(response.status_code))}")
            return False
            
    except Exception as e:
        print(f"\n   {vermelho('❌ ERRO: ' + str(e))}")
        return False


def testar_telegram(config):
    """Testa conexão com Telegram"""
    print(f"\n{azul('=' * 60)}")
    print(azul('📱 TESTANDO CONEXÃO COM TELEGRAM'))
    print(azul('=' * 60))
    
    if not config.get('token') or not config.get('chat_id'):
        print(f"\n   {amarelo('⚠️ Telegram não configurado (opcional)')}")
        return True
    
    try:
        import requests
        
        print(f"\n   Chat ID: {config['chat_id']}")
        
        response = requests.get(
            f"https://api.telegram.org/bot{config['token']}/getMe",
            timeout=10
        )
        
        if response.status_code == 200:
            bot = response.json().get('result', {})
            bot_username = bot.get('username', 'desconhecido')
            print(f"   {verde('✅ Bot conectado: @' + bot_username)}")
            
            enviar = input("\n   Enviar mensagem de teste? (s/N): ").strip().lower()
            
            if enviar == 's':
                msg_response = requests.post(
                    f"https://api.telegram.org/bot{config['token']}/sendMessage",
                    data={
                        'chat_id': config['chat_id'],
                        'text': '🤖 Teste de conexão do Bot de Publicações (v3.0) - OK!',
                        'parse_mode': 'HTML'
                    },
                    timeout=10
                )
                
                if msg_response.status_code == 200:
                    print(f"   {verde('✅ Mensagem enviada com sucesso!')}")
                else:
                    print(f"   {vermelho('❌ Erro ao enviar: ' + msg_response.text[:100])}")
            
            return True
        else:
            print(f"   {vermelho('❌ Erro: ' + str(response.status_code))}")
            return False
            
    except Exception as e:
        print(f"\n   {vermelho('❌ ERRO: ' + str(e))}")
        return False


def testar_lista_especial(config):
    """Testa carregamento da lista especial"""
    print(f"\n{azul('=' * 60)}")
    print(azul('📋 TESTANDO LISTA ESPECIAL'))
    print(azul('=' * 60))
    
    arquivo = config.get('arquivo', 'lista_especial.txt')
    print(f"\n   Arquivo: {arquivo}")
    
    if not os.path.exists(arquivo):
        print(f"   {amarelo('⚠️ Arquivo não encontrado (lista especial desativada)')}")
        return True
    
    try:
        nomes = []
        with open(arquivo, 'r', encoding='utf-8') as f:
            for linha in f:
                nome = linha.strip()
                if nome and not nome.startswith('#'):
                    nomes.append(nome)
        
        print(f"   {verde('✅ Lista carregada: ' + str(len(nomes)) + ' nomes')}")
        
        # Mostra alguns nomes
        if nomes:
            print("\n   Primeiros nomes da lista:")
            for nome in nomes[:5]:
                print(f"      - {nome}")
            if len(nomes) > 5:
                print(f"      ... e mais {len(nomes) - 5}")
        
        return True
        
    except Exception as e:
        print(f"\n   {vermelho('❌ ERRO: ' + str(e))}")
        return False


def main():
    """Função principal de teste"""
    print("\n" + "=" * 60)
    print("🧪 TESTE DE CONFIGURAÇÃO - Bot de Publicações (v3.0)")
    print("=" * 60)
    
    if not Path('config.json').exists():
        print(f"\n{vermelho('❌ Arquivo config.json não encontrado!')}")
        print("Crie o arquivo config.json com suas configurações.")
        input("\nPressione ENTER para sair...")
        sys.exit(1)
    
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    resultados = {}
    
    # Testa cada componente
    resultados['email'] = testar_email(config['email'])
    resultados['ia'] = testar_ia(config.get('ia', {'provedor': 'ollama', 'ollama': config.get('ollama', {})}))
    resultados['trello'] = testar_trello(config['trello'])
    resultados['telegram'] = testar_telegram(config['telegram'])
    resultados['lista_especial'] = testar_lista_especial(config.get('lista_especial', {}))
    
    # Resumo
    print(f"\n{azul('=' * 60)}")
    print(azul('📊 RESUMO DOS TESTES'))
    print(azul('=' * 60) + "\n")
    
    provedor = config.get('ia', {}).get('provedor', 'ollama').upper()
    
    componentes = {
        'email': '📧 Email/Gmail',
        'ia': f'🧠 IA ({provedor})',
        'trello': '📋 Trello',
        'telegram': '📱 Telegram',
        'lista_especial': '📋 Lista Especial'
    }
    
    todos_ok = True
    for key, nome in componentes.items():
        if resultados.get(key):
            print(f"   {verde('✅')} {nome}")
        else:
            print(f"   {vermelho('❌')} {nome}")
            if key not in ['telegram', 'lista_especial']:
                todos_ok = False
    
    print()
    
    if todos_ok:
        print(verde('✅ Todos os componentes essenciais estão funcionando!'))
        print("\nPara executar o bot:")
        print("   python bot.py           # Executa uma vez")
        print("   python bot.py --continuo # Executa continuamente")
        print("\nPara trocar de IA:")
        print(f'   Edite config.json → "ia" → "provedor": "ollama" ou "gemini"')
    else:
        print(vermelho('❌ Alguns componentes precisam de atenção.'))
        print("\nRevise as configurações no config.json")
    
    input("\nPressione ENTER para sair...")


if __name__ == "__main__":
    main()
