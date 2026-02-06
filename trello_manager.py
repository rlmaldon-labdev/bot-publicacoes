"""
Módulo para gerenciamento do Trello
Cria cards automaticamente com as informações processadas
Versão Opus - Com PF no título e limpeza de HTML
"""

import requests
import json
import re
import html as html_module
from datetime import datetime


class TrelloManager:
    def __init__(self, config):
        """Inicializa gerenciador do Trello"""
        self.api_key = config['api_key']
        self.token = config['token']
        self.board_id = config.get('board_id')
        self.lista_id = config['lista_id']
        
        self.base_url = "https://api.trello.com/1"
        
        # IDs das etiquetas (serão criadas se não existirem)
        self.etiquetas = {}
        self._setup_etiquetas()
    
    def _setup_etiquetas(self):
        """Cria ou busca etiquetas padrão"""
        etiquetas_padrao = {
            'a_revisar': {'nomes': ['🔴 A REVISAR', 'A REVISAR'], 'cor': 'red'},
            'revisado': {'nomes': ['🟢 REVISADO', 'REVISADO'], 'cor': 'green'},
            'urgente': {'nomes': ['⚡ URGENTE', 'URGENTE'], 'cor': 'yellow'},
            'prazo_implicito': {'nomes': ['⚠️ PRAZO IMPLÍCITO', 'PRAZO IMPLÍCITO', 'PRAZO IMPLICITO'], 'cor': 'orange'}
        }
        
        try:
            # Busca etiquetas existentes
            url = f"{self.base_url}/boards/{self.board_id}/labels"
            params = {'key': self.api_key, 'token': self.token}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                labels_existentes = response.json()
                
                # Mapeia etiquetas existentes
                for label in labels_existentes:
                    label_name = label['name'].upper().strip()
                    for key, config in etiquetas_padrao.items():
                        for nome_variacao in config['nomes']:
                            if nome_variacao.upper().strip() in label_name or label_name in nome_variacao.upper().strip():
                                self.etiquetas[key] = label['id']
                                print(f"   ✅ Etiqueta encontrada: {label['name']} → {key}")
                                break
                
                # Cria etiquetas faltantes
                for key, config in etiquetas_padrao.items():
                    if key not in self.etiquetas:
                        print(f"   ⚠️ Etiqueta '{key}' não encontrada, tentando criar...")
                        label_id = self._criar_etiqueta(config['nomes'][0], config['cor'])
                        if label_id:
                            self.etiquetas[key] = label_id
                            print(f"   ✅ Etiqueta criada: {config['nomes'][0]}")
            else:
                print(f"   ⚠️ Erro ao buscar etiquetas: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️ Erro ao configurar etiquetas: {e}")
    
    def _criar_etiqueta(self, nome, cor):
        """Cria uma nova etiqueta no board"""
        try:
            url = f"{self.base_url}/labels"
            params = {
                'key': self.api_key,
                'token': self.token,
                'idBoard': self.board_id,
                'name': nome,
                'color': cor
            }
            response = requests.post(url, data=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()['id']
            return None
        except:
            return None
    
    def criar_card(self, dados, email_data):
        """Cria card no Trello com os dados processados"""
        try:
            # Monta título do card (com PF - Prazo Fatal)
            titulo = self._montar_titulo(dados)
            
            # Monta descrição (com HTML limpo)
            descricao = self._montar_descricao(dados, email_data)
            
            # Prepara etiquetas
            etiquetas_card = []
            
            if 'a_revisar' in self.etiquetas:
                etiquetas_card.append(self.etiquetas['a_revisar'])
            
            if dados.get('urgente') and 'urgente' in self.etiquetas:
                etiquetas_card.append(self.etiquetas['urgente'])
            
            if dados.get('prazo_implicito') and 'prazo_implicito' in self.etiquetas:
                etiquetas_card.append(self.etiquetas['prazo_implicito'])
            
            # Converte data de entrega
            due_date = self._converter_data_prazo(dados.get('prazo_calculado'))
            
            # Cria card
            url = f"{self.base_url}/cards"
            params = {
                'key': self.api_key,
                'token': self.token,
                'idList': self.lista_id,
                'name': titulo,
                'desc': descricao,
                'due': due_date
            }
            
            # Adiciona etiquetas se houver
            if etiquetas_card:
                params['idLabels'] = ','.join(etiquetas_card)
            
            response = requests.post(url, data=params, timeout=15)
            
            if response.status_code == 200:
                card_data = response.json()
                
                # Cria checklist
                self._criar_checklist(card_data['id'])
                
                return {
                    'id': card_data['id'],
                    'url': card_data['url'],
                    'titulo': titulo
                }
            else:
                print(f"❌ Erro ao criar card: {response.status_code}")
                print(f"   Resposta: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Erro ao criar card no Trello: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _montar_titulo(self, dados):
        """
        Monta título do card com formato:
        PROCESSO (PF: DD/MM/YYYY) - CLIENTE - TIPO
        
        Prioriza: número do processo e prazo fatal (PF)
        Limite do Trello: ~512 caracteres, mas mantemos menor para legibilidade
        """
        processo = dados.get('numero_processo') or 'SEM NÚMERO'
        prazo = dados.get('prazo_calculado') or 'N/D'
        cliente = dados.get('cliente') or 'N/I'
        tipo = dados.get('tipo_ato') or 'ATO'
        
        # Monta parte fixa (processo + prazo) - isso é prioridade
        parte_fixa = f"{processo} (PF: {prazo})"
        
        # Calcula espaço restante para cliente e tipo
        # Limite seguro: 120 caracteres total para boa visualização
        LIMITE_TOTAL = 120
        espaco_restante = LIMITE_TOTAL - len(parte_fixa) - 6  # 6 = " - " + " - "
        
        if espaco_restante > 20:
            # Divide espaço entre cliente e tipo
            espaco_cliente = int(espaco_restante * 0.7)  # 70% para cliente
            espaco_tipo = espaco_restante - espaco_cliente
            
            # Trunca se necessário
            if len(cliente) > espaco_cliente:
                cliente = cliente[:espaco_cliente-2] + '..'
            
            if len(tipo) > espaco_tipo:
                tipo = tipo[:espaco_tipo-2] + '..'
            
            return f"{parte_fixa} - {cliente} - {tipo.upper()}"
        else:
            # Sem espaço: só processo e prazo
            return parte_fixa
    
    def _limpar_html_descricao(self, texto):
        """Remove tags HTML e limpa texto para descrição"""
        if not texto:
            return "Corpo não disponível"
        
        # Desescapa entidades HTML
        texto = html_module.unescape(texto)
        
        # Converte quebras HTML para quebras normais
        texto = re.sub(r'<\s*br\s*/?\s*>', '\n', texto, flags=re.IGNORECASE)
        texto = re.sub(r'</\s*p\s*>', '\n\n', texto, flags=re.IGNORECASE)
        texto = re.sub(r'</\s*div\s*>', '\n', texto, flags=re.IGNORECASE)
        
        # Remove todas as tags HTML
        texto = re.sub(r'<[^>]+>', ' ', texto)
        
        # Limpa espaços extras
        texto = re.sub(r'[ \t]+', ' ', texto)
        texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)
        
        # Remove caracteres de controle estranhos
        texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', texto)
        
        return texto.strip()
    
    def _montar_descricao(self, dados, email_data):
        """Monta descrição completa do card"""
        
        # Calcula nível de confiança
        confianca = dados.get('confianca', 0.5)
        nivel_confianca = "ALTA" if confianca >= 0.8 else "MÉDIA" if confianca >= 0.6 else "BAIXA"
        
        # Limpa e limita texto da publicação
        texto_publicacao = self._limpar_html_descricao(email_data.get('corpo', ''))
        MAX_TEXTO = 3000  # Limite seguro para Trello
        
        texto_truncado = len(texto_publicacao) > MAX_TEXTO
        if texto_truncado:
            texto_publicacao = texto_publicacao[:MAX_TEXTO]
        
        # Monta descrição
        descricao = f"""{'═'*50}
📄 TEXTO DA PUBLICAÇÃO
{'═'*50}

{texto_publicacao}

"""
        if texto_truncado:
            descricao += f"... (Texto truncado - total: {len(email_data.get('corpo', ''))} caracteres)\n\n"
        
        descricao += f"""{'═'*50}
🤖 RESUMO AUTOMÁTICO (CONFERIR!)
⚠️ CONFIANÇA: {nivel_confianca} ({int(confianca*100)}%)
{'═'*50}

📌 INFORMAÇÕES EXTRAÍDAS:

• Processo: {dados.get('numero_processo') or 'N/A'}
• Cliente: {dados.get('cliente') or 'N/A'}
• Tipo: {dados.get('tipo_ato') or 'N/A'}
• Tribunal: {dados.get('tribunal') or 'N/A'}
• Vara: {dados.get('vara') or 'N/A'}

📅 PRAZO:
"""
        
        # Adiciona informações de prazo
        if dados.get('prazo_calculado'):
            descricao += f"• Data limite: {dados['prazo_calculado']}\n"
        
        if dados.get('prazo_mencionado'):
            descricao += f"• Prazo mencionado: {dados['prazo_mencionado']}\n"
        elif dados.get('prazo_implicito'):
            descricao += "• ⚠️ Prazo não especificado (aplicado 5 dias úteis - CPC)\n"
        
        # Adiciona resumo em tópicos
        if dados.get('resumo_topicos'):
            descricao += f"\n📋 DETERMINAÇÕES:\n\n"
            for topico in dados['resumo_topicos'][:5]:
                topico_limpo = str(topico)[:200]
                descricao += f"• {topico_limpo}\n"
        
        # Adiciona observações
        if dados.get('observacoes'):
            obs = str(dados['observacoes'])[:300]
            descricao += f"\n⚠️ OBSERVAÇÕES:\n{obs}\n"
        
        # Avisos
        descricao += f"""
{'═'*50}
⚠️ ATENÇÃO
{'═'*50}
"""
        
        if dados.get('prazo_implicito'):
            descricao += """
🔴 PRAZO NÃO ESPECIFICADO NA PUBLICAÇÃO

Prazo calculado: 5 dias úteis (regra geral CPC art. 231)

Revisar:
- Confirmar se aplica prazo geral
- Verificar caso específico
- Validar dias úteis vs corridos
"""
        
        if dados.get('urgente'):
            descricao += "\n⚡ URGENTE! Publicação contém menção a urgência.\n"
        
        descricao += f"""
{'═'*50}

⚠️ Resumo gerado por IA - SEMPRE conferir texto original!

🤖 Processado: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
"""
        
        # Garante limite total
        if len(descricao) > 15000:
            descricao = descricao[:15000] + "\n\n... (Descrição truncada)"
        
        return descricao
    
    def _converter_data_prazo(self, data_str):
        """Converte data de DD/MM/YYYY para formato Trello (ISO)"""
        if not data_str:
            return None
        
        try:
            partes = data_str.split('/')
            if len(partes) == 3:
                dia, mes, ano = partes
                # Trello espera: YYYY-MM-DDTHH:MM:SS.000Z
                return f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}T12:00:00.000Z"
        except:
            pass
        
        return None
    
    def _criar_checklist(self, card_id):
        """Cria checklist no card"""
        try:
            url = f"{self.base_url}/checklists"
            params = {
                'key': self.api_key,
                'token': self.token,
                'idCard': card_id,
                'name': 'Ações Necessárias'
            }
            response = requests.post(url, data=params, timeout=10)
            
            if response.status_code == 200:
                checklist_id = response.json()['id']
                
                itens = [
                    '☐ Revisar prazo calculado',
                    '☐ Conferir dados extraídos',
                    '☐ Verificar texto integral',
                    '☐ Preparar providências',
                    '☐ Mudar para 🟢 REVISADO'
                ]
                
                for item in itens:
                    self._adicionar_item_checklist(checklist_id, item)
        except Exception as e:
            print(f"⚠️ Erro ao criar checklist: {e}")
    
    def _adicionar_item_checklist(self, checklist_id, nome):
        """Adiciona item na checklist"""
        try:
            url = f"{self.base_url}/checklists/{checklist_id}/checkItems"
            params = {
                'key': self.api_key,
                'token': self.token,
                'name': nome
            }
            requests.post(url, data=params, timeout=5)
        except:
            pass
