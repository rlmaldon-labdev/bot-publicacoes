"""
Módulo para processamento com IA (Ollama local ou Gemini API)
Extrai informações estruturadas de publicações jurídicas
Versão 3.0 - Suporte multi-provedor
"""

import requests
import json
import re
from datetime import datetime, timedelta
from abc import ABC, abstractmethod


class IAProvedor(ABC):
    """Classe base para provedores de IA"""
    
    @abstractmethod
    def gerar_resposta(self, prompt):
        pass
    
    @abstractmethod
    def testar_conexao(self):
        pass


class OllamaProvedor(IAProvedor):
    """Provedor Ollama (local)"""
    
    def __init__(self, config):
        self.url = config.get('url', 'http://localhost:11434')
        self.modelo = config.get('modelo', 'llama3.1:8b-instruct-q4_K_M')
        self.temperatura = config.get('temperatura', 0.3)
        self.max_tokens = config.get('max_tokens', 2000)
    
    def testar_conexao(self):
        """Testa se Ollama está acessível"""
        try:
            response = requests.get(f"{self.url}/api/tags", timeout=10)
            if response.status_code == 200:
                modelos = response.json().get('models', [])
                modelo_encontrado = any(
                    m.get('name', '').startswith(self.modelo.split(':')[0]) 
                    for m in modelos
                )
                if modelo_encontrado:
                    return True, f"Ollama conectado - Modelo: {self.modelo}"
                else:
                    return False, f"Modelo '{self.modelo}' não encontrado. Disponíveis: {[m.get('name') for m in modelos]}"
            return False, "Ollama não respondeu corretamente"
        except requests.exceptions.ConnectionError:
            return False, f"Não foi possível conectar ao Ollama em {self.url}"
        except Exception as e:
            return False, f"Erro ao conectar: {e}"
    
    def gerar_resposta(self, prompt):
        """Gera resposta usando Ollama"""
        try:
            response = requests.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.modelo,
                    "prompt": prompt,
                    "temperature": self.temperatura,
                    "stream": False,
                    "options": {"num_predict": self.max_tokens}
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json().get('response', '')
            return None
        except Exception as e:
            print(f"❌ Erro Ollama: {e}")
            return None


class GeminiProvedor(IAProvedor):
    """Provedor Google Gemini (API)"""
    
    def __init__(self, config):
        self.api_key = config.get('api_key', '')
        self.modelo = config.get('modelo', 'gemini-2.5-flash')
        self.temperatura = config.get('temperatura', 0.3)
        self.max_tokens = config.get('max_tokens', 2000)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    
    def testar_conexao(self):
        """Testa se Gemini API está acessível"""
        if not self.api_key:
            return False, "API Key do Gemini não configurada"
        
        try:
            url = f"{self.base_url}/{self.modelo}:generateContent?key={self.api_key}"
            response = requests.post(
                url,
                json={
                    "contents": [{"parts": [{"text": "Responda apenas: OK"}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 10}
                },
                timeout=15
            )
            
            if response.status_code == 200:
                return True, f"Gemini conectado - Modelo: {self.modelo}"
            elif response.status_code == 400:
                error = response.json().get('error', {}).get('message', 'Erro desconhecido')
                return False, f"Erro na API Gemini: {error}"
            elif response.status_code == 403:
                return False, "API Key inválida ou sem permissão"
            else:
                return False, f"Gemini retornou status {response.status_code}"
        except Exception as e:
            return False, f"Erro ao conectar: {e}"
    
    def gerar_resposta(self, prompt):
        """Gera resposta usando Gemini"""
        try:
            url = f"{self.base_url}/{self.modelo}:generateContent?key={self.api_key}"
            response = requests.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": self.temperatura,
                        "maxOutputTokens": self.max_tokens,
                        "responseMimeType": "application/json"
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                candidates = data.get('candidates', [])
                if candidates:
                    content = candidates[0].get('content', {})
                    parts = content.get('parts', [])
                    if parts:
                        return parts[0].get('text', '')
            else:
                print(f"❌ Erro Gemini: {response.status_code} - {response.text[:200]}")
            return None
        except Exception as e:
            print(f"❌ Erro Gemini: {e}")
            return None


class LLMProcessor:
    """Processador principal que usa Ollama ou Gemini"""
    
    def __init__(self, config):
        """Inicializa processador com provedor configurado"""
        self.config = config
        
        # Determina qual provedor usar
        provedor_nome = config.get('provedor', 'ollama').lower()
        
        if provedor_nome == 'gemini':
            self.provedor = GeminiProvedor(config.get('gemini', {}))
            self.provedor_nome = 'Gemini'
        else:
            self.provedor = OllamaProvedor(config.get('ollama', {}))
            self.provedor_nome = 'Ollama'
        
        # Testa conexão
        sucesso, mensagem = self.provedor.testar_conexao()
        if sucesso:
            print(f"   ✅ {mensagem}")
        else:
            print(f"   ❌ {mensagem}")
            raise Exception(f"Falha ao conectar com {self.provedor_nome}: {mensagem}")
    
    def get_provedor_info(self):
        """Retorna informações do provedor atual"""
        return self.provedor_nome
    
    def _extrair_data_publicacao(self, texto):
        """Extrai a data de publicação do texto"""
        # Padrão: "Data de Publicação: DD/MM/YYYY" ou variações
        match = re.search(
            r'data\s+de\s+publica[çc][aã]o\s*:\s*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
            texto, re.IGNORECASE
        )
        
        if match:
            dia, mes, ano = match.groups()
            try:
                return datetime(int(ano), int(mes), int(dia))
            except ValueError:
                pass
        
        # Padrão 2: "Publicação: DD/MM/YYYY"
        match = re.search(
            r'publica[çc][aã]o[^0-9]*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
            texto, re.IGNORECASE
        )
        
        if match:
            dia, mes, ano = match.groups()
            try:
                return datetime(int(ano), int(mes), int(dia))
            except ValueError:
                pass
        
        return datetime.now()
    
    def extrair_dados(self, texto_publicacao):
        """Extrai dados estruturados da publicação usando IA"""
        
        data_publicacao = self._extrair_data_publicacao(texto_publicacao)
        texto_limitado = texto_publicacao[:8000] if len(texto_publicacao) > 8000 else texto_publicacao
        
        prompt = self._montar_prompt(texto_limitado, data_publicacao)
        
        try:
            resposta = self.provedor.gerar_resposta(prompt)
            
            if resposta:
                dados = self._extrair_json(resposta)
                
                if dados:
                    dados['data_publicacao'] = data_publicacao.strftime("%d/%m/%Y")
                    dados['prazo_calculado'] = self._calcular_prazo(dados, data_publicacao)
                    dados['processado_em'] = datetime.now().isoformat()
                    dados['provedor_ia'] = self.provedor_nome
                    return dados
            
            print("⚠️ IA não retornou JSON válido, tentando extração básica...")
            return self._extrair_dados_basico(texto_publicacao, data_publicacao)
            
        except Exception as e:
            print(f"❌ Erro ao processar: {e}")
            return self._extrair_dados_basico(texto_publicacao, data_publicacao)
    
    def _montar_prompt(self, texto, data_publicacao):
        """Monta prompt para extração de dados jurídicos"""
        
        return f"""Você é um assistente especializado em análise de publicações jurídicas brasileiras.

Analise a publicação abaixo e extraia as informações em formato JSON.

PUBLICAÇÃO:
{texto}

INSTRUÇÕES:
1. Extraia o número do processo (formato CNJ: 0000000-00.0000.0.00.0000)
2. Identifique o nome do cliente/parte principal (POLO ATIVO geralmente é nosso cliente)
3. Identifique o tipo de ato (intimação, citação, decisão, sentença, despacho, etc)
4. Identifique o tribunal/órgão
5. Identifique a vara/juízo
6. IMPORTANTE: Extraia o prazo em DIAS se mencionado (ex: "prazo de 15 dias", "5 dias úteis")
7. Se não houver prazo expresso, marque "prazo_implicito": true e "prazo_dias": 5
8. Crie um resumo em tópicos curtos do que foi determinado
9. Identifique se há urgência

ATENÇÃO AO PRAZO:
- Se mencionar "prazo de 15 dias" → prazo_dias: 15
- Se mencionar "prazo de 5 dias" → prazo_dias: 5
- Se não mencionar prazo → prazo_implicito: true, prazo_dias: 5
- Prazos são sempre em dias ÚTEIS, exceto se disser "dias corridos"

FORMATO DE SAÍDA (APENAS JSON, sem explicações):
{{
  "numero_processo": "0000000-00.0000.0.00.0000",
  "cliente": "Nome da Parte",
  "tipo_ato": "Tipo do Ato",
  "tribunal": "Nome do Tribunal",
  "vara": "Nome da Vara",
  "prazo_mencionado": "15 dias" ou null,
  "prazo_implicito": false,
  "prazo_dias": 15,
  "prazo_tipo": "úteis",
  "resumo_topicos": ["Tópico 1", "Tópico 2"],
  "urgente": false,
  "observacoes": "Observações importantes",
  "confianca": 0.85
}}

IMPORTANTE: Retorne APENAS o JSON, sem markdown, sem explicações.

JSON:"""
    
    def _extrair_json(self, texto):
        """Extrai JSON da resposta da IA"""
        try:
            texto = texto.replace('```json', '').replace('```', '').strip()
            match = re.search(r'\{.*\}', texto, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return json.loads(texto)
        except Exception as e:
            print(f"⚠️ Erro ao extrair JSON: {e}")
            return None
    
    def _extrair_dados_basico(self, texto, data_publicacao):
        """Extração básica via regex (fallback)"""
        dados = {
            'numero_processo': None,
            'cliente': None,
            'tipo_ato': 'Ato não identificado',
            'tribunal': None,
            'vara': None,
            'prazo_mencionado': None,
            'prazo_implicito': True,
            'prazo_dias': 5,
            'prazo_tipo': 'úteis',
            'resumo_topicos': ['Verificar manualmente'],
            'urgente': False,
            'observacoes': 'Extração via regex (fallback)',
            'confianca': 0.3,
            'data_publicacao': data_publicacao.strftime("%d/%m/%Y"),
            'processado_em': datetime.now().isoformat(),
            'provedor_ia': self.provedor_nome
        }
        
        # Extrai número CNJ
        cnj_match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
        if cnj_match:
            dados['numero_processo'] = cnj_match.group(1)
        
        # Extrai POLO ATIVO
        polo_match = re.search(r'POLO\s+ATIVO\s*:\s*([^\n]+)', texto, re.IGNORECASE)
        if polo_match:
            dados['cliente'] = polo_match.group(1).strip()
        
        # Identifica tipo de ato
        tipos_ato = [
            ('sentença', 'Sentença'), ('decisão', 'Decisão'),
            ('despacho', 'Despacho'), ('intimação', 'Intimação'),
            ('citação', 'Citação'), ('ato ordinatório', 'Ato Ordinatório')
        ]
        
        texto_lower = texto.lower()
        for termo, tipo in tipos_ato:
            if termo in texto_lower:
                dados['tipo_ato'] = tipo
                break
        
        # Extrai prazo
        prazo_match = re.search(r'prazo\s+de\s+(\d+)\s+dias?', texto_lower)
        if prazo_match:
            dados['prazo_dias'] = int(prazo_match.group(1))
            dados['prazo_implicito'] = False
        
        dados['prazo_calculado'] = self._calcular_prazo(dados, data_publicacao)
        return dados
    
    def _calcular_prazo(self, dados, data_publicacao):
        """Calcula data do prazo a partir da data de publicação"""
        try:
            dias = int(dados.get('prazo_dias', 5))
            tipo = dados.get('prazo_tipo', 'úteis')
            
            # Inicia no dia SEGUINTE à publicação
            data_inicio = data_publicacao + timedelta(days=1)
            
            # Se não for dia útil, avança
            while data_inicio.weekday() >= 5:
                data_inicio += timedelta(days=1)
            
            if tipo == 'úteis':
                prazo_final = self._adicionar_dias_uteis(data_inicio, dias)
            else:
                prazo_final = data_inicio + timedelta(days=dias - 1)
            
            return prazo_final.strftime("%d/%m/%Y")
        except Exception as e:
            print(f"⚠️ Erro ao calcular prazo: {e}")
            return None
    
    def _adicionar_dias_uteis(self, data_inicial, dias):
        """Adiciona dias úteis"""
        data_atual = data_inicial
        dias_contados = 1
        
        while dias_contados < dias:
            data_atual += timedelta(days=1)
            if data_atual.weekday() < 5:
                dias_contados += 1
        
        return data_atual
