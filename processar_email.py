"""
Módulo para processamento de emails (IMAP)
Conecta ao Gmail via label e busca emails com publicações
Versão Opus - Corrigida e otimizada
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import re
import html as html_module
import unicodedata


class EmailProcessor:
    def __init__(self, config):
        """Inicializa processador de email"""
        self.servidor = config['servidor']
        self.porta = config['porta']
        self.usuario = config['usuario']
        self.senha = config['senha']
        self.label = config.get('label', '')
        self.marcar_como_lido = config.get('marcar_como_lido_apos_processar', True)
        
        self.mail = None
        self._conectar()
    
    def _conectar(self):
        """Conecta ao servidor IMAP"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.servidor, self.porta)
            self.mail.login(self.usuario, self.senha)
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar ao email: {e}")
            raise
    
    def _selecionar_label(self):
        """Seleciona a label/pasta correta no Gmail"""
        if self.label:
            # Gmail usa formato especial para labels
            # Tenta diferentes formatos
            formatos = [
                f'"{self.label}"',
                f'"[Gmail]/{self.label}"',
                self.label,
                f'INBOX/{self.label}'
            ]
            
            for formato in formatos:
                try:
                    status, _ = self.mail.select(formato)
                    if status == 'OK':
                        print(f"   ✅ Label selecionada: {formato}")
                        return True
                except:
                    continue
            
            # Se não encontrou, lista labels disponíveis para debug
            print(f"   ⚠️ Label '{self.label}' não encontrada. Labels disponíveis:")
            status, labels = self.mail.list()
            if status == 'OK':
                for label in labels[:10]:  # Mostra primeiras 10
                    print(f"      - {label.decode()}")
            
            # Fallback para INBOX
            print(f"   ℹ️ Usando INBOX como fallback")
            self.mail.select('INBOX')
            return False
        else:
            self.mail.select('INBOX')
            return True
    
    def buscar_emails_novos(self, dias=7):
        """Busca emails não lidos na label configurada"""
        try:
            # Reconecta se necessário
            if not self.mail or self.mail.state != 'SELECTED':
                self._conectar()
            
            # Seleciona a label
            self._selecionar_label()
            
            # Busca emails não lidos
            status, messages = self.mail.search(None, 'UNSEEN')
            
            if status != 'OK':
                print("❌ Erro ao buscar emails")
                return []
            
            email_ids = messages[0].split()
            
            if not email_ids:
                return []
            
            print(f"   📬 {len(email_ids)} email(s) não lido(s) encontrado(s)")
            
            # Processa cada email
            emails_processados = []
            
            for email_id in email_ids:
                try:
                    email_data = self._processar_email(email_id)
                    if email_data:
                        # Separa múltiplas publicações do email
                        publicacoes = self.separar_publicacoes(email_data['corpo'])
                        
                        if publicacoes:
                            for pub in publicacoes:
                                # Cria uma cópia do email_data para cada publicação
                                pub_data = email_data.copy()
                                pub_data['corpo'] = pub['texto']
                                pub_data['numero_publicacao'] = pub['numero']
                                pub_data['total_publicacoes'] = len(publicacoes)
                                emails_processados.append(pub_data)
                        else:
                            # Fallback: usa o email inteiro como uma publicação
                            email_data['numero_publicacao'] = 1
                            email_data['total_publicacoes'] = 1
                            emails_processados.append(email_data)
                            
                except Exception as e:
                    print(f"⚠️ Erro ao processar email {email_id}: {e}")
                    continue
            
            return emails_processados
            
        except Exception as e:
            print(f"❌ Erro ao buscar emails: {e}")
            return []
    
    def _processar_email(self, email_id):
        """Processa um email individual"""
        try:
            # Busca email (sem marcar como lido ainda)
            status, msg_data = self.mail.fetch(email_id, '(BODY.PEEK[])')
            
            if status != 'OK':
                return None
            
            # Parse do email
            msg = email.message_from_bytes(msg_data[0][1])
            
            # Extrai dados
            assunto = self._decodificar_header(msg['Subject'])
            remetente = self._decodificar_header(msg['From'])
            data = msg['Date']
            
            # Extrai corpo (com limpeza de HTML)
            corpo = self._extrair_corpo(msg)
            
            return {
                'id': email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                'assunto': assunto,
                'remetente': remetente,
                'data': data,
                'corpo': corpo
            }
            
        except Exception as e:
            print(f"❌ Erro ao processar email: {e}")
            return None
    
    def _decodificar_header(self, header):
        """Decodifica header do email"""
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        result = []
        
        for content, encoding in decoded_parts:
            if isinstance(content, bytes):
                try:
                    result.append(content.decode(encoding or 'utf-8'))
                except:
                    result.append(content.decode('utf-8', errors='ignore'))
            else:
                result.append(str(content))
        
        return ''.join(result)
    
    def _extrair_corpo(self, msg):
        """Extrai corpo do email, limpando HTML se necessário"""
        corpo_texto = ""
        corpo_html = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                
                try:
                    payload = part.get_payload(decode=True)
                    if payload is None:
                        continue
                    charset = part.get_content_charset() or 'utf-8'
                    texto = payload.decode(charset, errors='ignore')
                    
                    if content_type == 'text/plain':
                        corpo_texto = texto
                    elif content_type == 'text/html':
                        corpo_html = texto
                except:
                    continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                content_type = msg.get_content_type()
                
                if payload:
                    texto = payload.decode(charset, errors='ignore')
                    if content_type == 'text/html':
                        corpo_html = texto
                    else:
                        corpo_texto = texto
            except:
                corpo_texto = str(msg.get_payload())
        
        # Prioriza texto puro, mas limpa HTML se necessário
        if corpo_texto.strip():
            return self._limpar_texto(corpo_texto)
        elif corpo_html.strip():
            return self._html_para_texto(corpo_html)
        else:
            return ""
    
    def _html_para_texto(self, html_content):
        """Converte HTML para texto limpo"""
        if not html_content:
            return ""
        
        # Desescapa entidades HTML
        texto = html_module.unescape(html_content)
        
        # Converte <br> e </p> para quebras de linha
        texto = re.sub(r'<\s*br\s*/?\s*>', '\n', texto, flags=re.IGNORECASE)
        texto = re.sub(r'</\s*p\s*>', '\n\n', texto, flags=re.IGNORECASE)
        texto = re.sub(r'</\s*div\s*>', '\n', texto, flags=re.IGNORECASE)
        texto = re.sub(r'</\s*tr\s*>', '\n', texto, flags=re.IGNORECASE)
        texto = re.sub(r'</\s*li\s*>', '\n', texto, flags=re.IGNORECASE)
        
        # Remove todas as tags HTML
        texto = re.sub(r'<[^>]+>', ' ', texto)
        
        # Limpa espaços extras
        texto = re.sub(r'[ \t]+', ' ', texto)
        texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)
        
        return texto.strip()
    
    def _limpar_texto(self, texto):
        """Limpa texto de caracteres estranhos e espaços extras"""
        if not texto:
            return ""
        
        # Remove espaços extras
        texto = re.sub(r'[ \t]+', ' ', texto)
        texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)
        
        return texto.strip()
    
    def separar_publicacoes(self, texto_email):
        """
        Separa múltiplas publicações de um email em publicações individuais.
        Busca pelo padrão "Publicação: N." onde N é o número da publicação.
        """
        if not texto_email:
            return []
        
        # Normaliza o texto para busca (remove acentos para matching)
        def remover_acentos(s):
            return ''.join(
                ch for ch in unicodedata.normalize('NFKD', s) 
                if not unicodedata.combining(ch)
            )
        
        texto_norm = remover_acentos(texto_email.lower())
        texto_original = texto_email  # Guarda original para extração
        
        publicacoes = []
        
        # Padrão ESPECÍFICO: "Publicação: N." no INÍCIO de linha ou após quebra
        # Isso evita pegar "Data de Publicação:" que aparece dentro de cada publicação
        # O padrão correto é: Publicação: 1. / Publicação: 2. etc (com ponto após número)
        pub_regex = re.compile(
            r'(?:^|\n)\s*publica(?:c[aã]o|gao)\s*:\s*(\d+)\s*\.',
            re.IGNORECASE | re.MULTILINE
        )
        
        matches = list(pub_regex.finditer(texto_norm))
        
        if matches:
            for i, match in enumerate(matches):
                numero = int(match.group(1))
                
                # Pega desde o INÍCIO do marcador
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(texto_original)
                
                # Extrai bloco do texto ORIGINAL (não normalizado)
                bloco = texto_original[start:end].strip()
                
                # Remove possível \n do início
                bloco = bloco.lstrip('\n').strip()
                
                # Valida se tem conteúdo relevante (número CNJ ou PROCESSO)
                tem_cnj = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', bloco)
                tem_processo = re.search(r'PROCESSO\s*[N°:\d]', bloco, re.IGNORECASE)
                
                if bloco and (tem_cnj or tem_processo):
                    publicacoes.append({
                        'numero': numero,
                        'texto': bloco
                    })
        
        # Padrão 2 (fallback): Separa por número CNJ se não encontrou publicações
        if not publicacoes:
            cnj_regex = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
            cnj_matches = list(cnj_regex.finditer(texto_email))
            
            if len(cnj_matches) >= 1:
                for i, match in enumerate(cnj_matches):
                    start = match.start()
                    end = cnj_matches[i + 1].start() if i + 1 < len(cnj_matches) else len(texto_email)
                    
                    bloco = texto_email[start:end].strip()
                    
                    if len(bloco) > 50:
                        publicacoes.append({
                            'numero': i + 1,
                            'texto': bloco
                        })
        
        # Último recurso: texto inteiro como uma publicação
        if not publicacoes and len(texto_email) > 30:
            tem_cnj = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto_email)
            if tem_cnj:
                publicacoes.append({
                    'numero': 1,
                    'texto': texto_email
                })
        
        return publicacoes
    
    def marcar_email_como_lido(self, email_id):
        """Marca email como lido"""
        try:
            if isinstance(email_id, str):
                email_id = email_id.encode()
            
            self.mail.store(email_id, '+FLAGS', '\\Seen')
            return True
        except Exception as e:
            print(f"⚠️ Erro ao marcar email como lido: {e}")
            return False
    
    def marcar_email_como_nao_lido(self, email_id):
        """Marca email como não lido"""
        try:
            if isinstance(email_id, str):
                email_id = email_id.encode()
            
            self.mail.store(email_id, '-FLAGS', '\\Seen')
            return True
        except Exception as e:
            print(f"⚠️ Erro ao marcar email como não lido: {e}")
            return False
    
    def desconectar(self):
        """Desconecta do servidor"""
        try:
            if self.mail:
                self.mail.close()
                self.mail.logout()
        except:
            pass
