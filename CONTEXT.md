# CONTEXT - bot-publicacoes

## Objetivo
Automatizar o processamento de publicacoes juridicas vindas por email.
Fluxo principal: ler email IMAP -> extrair dados com IA -> criar card no Trello -> notificar no Telegram.

## Entrada e saida
- Entrada: emails da label configurada, `lista_especial.txt`, configuracoes do `config.json`.
- Saida: cards no Trello, mensagens no Telegram, logs em console/arquivo.

## Fluxo tecnico
1. `bot.py` inicializa todos os componentes (email, IA, Trello, Telegram, lista especial).
2. `processar_email.py` busca emails/publicacoes novas.
3. `bot.py` aplica filtro da lista especial (ignora clientes configurados).
4. `processar_llm.py` extrai JSON estruturado da publicacao (Ollama ou Gemini).
5. `trello_manager.py` cria card com dados extraidos e prazo.
6. `telegram_bot.py` envia notificacao e resumo.

## Arquivos-chave
- `bot.py`: orquestracao principal e modo continuo (`--continuo`).
- `processar_email.py`: leitura de emails/publicacoes.
- `processar_llm.py`: provedores IA (`ollama` e `gemini`) e parse de resposta.
- `trello_manager.py`: criacao de card.
- `telegram_bot.py`: notificacoes.
- `testar_configuracao.py`: validacao de integracoes.
- `config.json`: configuracao ativa do bot.
- `README.txt`: guia de uso operacional.

## Configuracao critica (`config.json`)
- `email`: servidor, porta, usuario, senha app, label.
- `ia.provedor`: `ollama` ou `gemini`.
- `ia.ollama`: `url`, `modelo`, `temperatura`, `max_tokens`.
- `ia.gemini`: `api_key`, `modelo`, `temperatura`, `max_tokens`.
- `trello`: `api_key`, `token`, `board_id`, `lista_id`.
- `telegram`: `token`, `chat_id`.
- `processamento`: `intervalo_minutos`, `dias_verificar`, `debug`, `log_file`.

## Comandos rapidos
- Execucao unica: `python bot.py`
- Execucao continua: `python bot.py --continuo`
- Testes de config: `python testar_configuracao.py`
- Atalhos Windows: `RodarBot.bat`, `RodarBotContinuo.bat`, `TestarTudo.bat`

## Riscos comuns
- Credenciais invalidas (Gmail, Trello, Telegram, Gemini/Ollama).
- Label de email incorreta.
- Modelo IA inexistente ou indisponivel.
- Lista especial com nomes mal normalizados.

## Retomada rapida (prompt sugerido)
"Use `bot-publicacoes/CONTEXT.md` como base. Trabalhe apenas em [arquivos]. Objetivo: [objetivo]. Nao varrer o projeto inteiro."

## Regra operacional
Nao commitar segredos (tokens, chaves, senhas) em `config.json` ou `.env`.
