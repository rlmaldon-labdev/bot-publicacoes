================================================================================
BOT DE PUBLICAÇÕES JURÍDICAS - GUIA COMPLETO
Versão 3.0
================================================================================

Este bot processa automaticamente publicações jurídicas recebidas por email,
extrai informações usando IA e cria cards no Trello.

================================================================================
FUNCIONALIDADES
================================================================================

✅ Lê emails de publicações jurídicas (OAB/MG)
✅ Extrai dados com IA (Ollama local OU Gemini API)
✅ Cria cards no Trello com prazos calculados
✅ Envia notificações no Telegram
✅ Lista especial: ignora publicações de clientes específicos
✅ Funciona em qualquer PC (com ou sem GPU)

================================================================================
REQUISITOS
================================================================================

1. Python 3.8 ou superior
   - Download: https://www.python.org/downloads/
   - Marque "Add Python to PATH" durante instalação

2. Dependências Python:
   pip install requests

3. Para usar Ollama (IA local):
   - Requer GPU com pelo menos 6GB VRAM (recomendado 8GB+)
   - Download: https://ollama.ai
   - Após instalar, execute: ollama pull llama3.1:8b-instruct-q4_K_M

4. Para usar Gemini (IA na nuvem):
   - Não requer GPU
   - Funciona em qualquer PC com internet
   - API Key gratuita: https://aistudio.google.com/apikey

================================================================================
ESTRUTURA DE ARQUIVOS
================================================================================

BotPublicacoesJuridicas/
├── bot.py                  # Programa principal
├── processar_email.py      # Módulo de email
├── processar_llm.py        # Módulo de IA (Ollama/Gemini)
├── trello_manager.py       # Módulo do Trello
├── telegram_bot.py         # Módulo do Telegram
├── testar_configuracao.py  # Script de teste
├── config.json             # Suas configurações (EDITAR!)
├── lista_especial.txt      # Nomes para ignorar (EDITAR!)
├── google_credentials.json # Credenciais Google (se usar)
├── RodarBot.bat            # Executa uma vez
├── RodarBotContinuo.bat    # Executa em loop
├── TestarTudo.bat          # Testa configuração
└── README.txt              # Este arquivo

================================================================================
CONFIGURAÇÃO - config.json
================================================================================

{
  "email": {
    "servidor": "imap.gmail.com",
    "porta": 993,
    "usuario": "SEU_EMAIL@gmail.com",
    "senha": "SUA_SENHA_DE_APP",          ← Senha de App do Gmail
    "label": "Publicacoes_OABMG",          ← Nome da label (sem acentos)
    "marcar_como_lido_apos_processar": true
  },
  
  "ia": {
    "provedor": "ollama",                  ← Mude para "gemini" se preferir
    
    "ollama": {
      "url": "http://localhost:11434",
      "modelo": "llama3.1:8b-instruct-q4_K_M"
    },
    
    "gemini": {
      "api_key": "SUA_API_KEY_GEMINI",
      "modelo": "gemini-2.5-flash"         ← Modelo gratuito
    }
  },
  
  "lista_especial": {
    "arquivo": "lista_especial.txt",
    "acao": "ignorar"
  },
  
  "trello": { ... },
  "telegram": { ... }
}

================================================================================
COMO TROCAR ENTRE OLLAMA E GEMINI
================================================================================

Para usar OLLAMA (local, requer GPU):
  1. Certifique-se que o Ollama está rodando (ollama serve)
  2. No config.json, coloque: "provedor": "ollama"

Para usar GEMINI (nuvem, qualquer PC):
  1. Obtenha API Key em: https://aistudio.google.com/apikey
  2. No config.json, coloque: "provedor": "gemini"
  3. Preencha a api_key em "gemini"

Modelos Gemini disponíveis:
  - gemini-2.5-flash  (recomendado, rápido, gratuito)
  - gemini-1.5-flash  (alternativa)
  - gemini-1.5-pro    (mais poderoso, pode ter limites)

================================================================================
LISTA ESPECIAL - lista_especial.txt
================================================================================

Este arquivo contém nomes de clientes que devem ser IGNORADOS.
Quando uma publicação mencionar esses nomes, o card NÃO será criado.

Formato do arquivo (um nome por linha):
  FULANO DE TAL
  EMPRESA XYZ LTDA
  CICLANO DA SILVA

Dicas:
  - Coloque variações com e sem acento
  - Use MAIÚSCULAS (o bot ignora maiúsculas/minúsculas)
  - Linhas começando com # são ignoradas (comentários)

================================================================================
COMO USAR
================================================================================

PRIMEIRA VEZ:
1. Edite config.json com suas credenciais
2. Edite lista_especial.txt com os nomes para ignorar
3. Execute TestarTudo.bat para verificar
4. Se tudo OK, execute RodarBot.bat

DIA A DIA:
- RodarBot.bat → Processa uma vez e fecha
- RodarBotContinuo.bat → Fica rodando a cada 15 minutos

================================================================================
USANDO EM OUTRO PC (SEM GPU)
================================================================================

Se o PC não tem GPU ou tem GPU fraca:

1. Copie toda a pasta do bot para o novo PC
2. Instale Python: https://www.python.org/downloads/
3. Instale dependências: pip install requests
4. Edite config.json:
   - Mude "provedor": "ollama" para "provedor": "gemini"
   - Preencha a api_key do Gemini
5. Execute TestarTudo.bat para verificar
6. Execute RodarBot.bat

NÃO precisa instalar Ollama no PC sem GPU!

================================================================================
LIMITES DO GEMINI GRATUITO
================================================================================

O plano gratuito do Gemini é generoso:
- 15 requisições por minuto
- 1.500 requisições por dia
- 1 milhão de tokens por minuto

Para seu uso (dezenas de publicações por dia), é mais que suficiente!

================================================================================
SOLUÇÃO DE PROBLEMAS
================================================================================

ERRO: "Ollama não conectado"
  → Certifique-se que o Ollama está rodando (ollama serve)
  → Ou mude para Gemini no config.json

ERRO: "API Key inválida"
  → Verifique a api_key do Gemini no config.json
  → Gere nova key em: https://aistudio.google.com/apikey

ERRO: "Label não encontrada"
  → Use nome da label SEM acentos
  → Confira o nome exato no Gmail

ERRO: "Board não encontrado"
  → Use o ID completo do board (não o shortLink)
  → Veja o ID em: https://api.trello.com/1/members/me/boards?key=SUA_KEY&token=SEU_TOKEN

================================================================================
SUPORTE
================================================================================

Para dúvidas ou problemas, verifique:
1. Execute TestarTudo.bat para diagnóstico
2. Confira se config.json está correto
3. Verifique se as APIs estão funcionando

================================================================================
