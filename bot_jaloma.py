"""
BOT DE PROCESSAMENTO DE PUBLICACOES JURIDICAS
Modo JalomaPrazos

Processa publicacoes por email, extrai dados com IA e cria cards direto no Jaloma.
Mantem o bot antigo intacto e remove o uso de Telegram nesta versao.
"""

import json
import os
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from jaloma_manager import JalomaManager
from processar_email import EmailProcessor
from processar_llm import LLMProcessor


class ListaEspecial:
    def __init__(self, config):
        self.nomes = []
        self.acao = config.get("acao", "ignorar")

        arquivo = config.get("arquivo", "lista_especial.txt")
        if os.path.exists(arquivo):
            with open(arquivo, "r", encoding="utf-8") as file:
                for linha in file:
                    nome = linha.strip()
                    if nome and not nome.startswith("#"):
                        self.nomes.append(self._normalizar(nome))
            print(f"   Lista especial carregada: {len(self.nomes)} nome(s)")
        else:
            print(f"   Aviso: arquivo {arquivo} nao encontrado (lista especial vazia)")

    def _normalizar(self, texto):
        texto = texto.upper()
        texto = unicodedata.normalize("NFKD", texto)
        return "".join(ch for ch in texto if not unicodedata.combining(ch))

    def verificar(self, texto_publicacao):
        texto_norm = self._normalizar(texto_publicacao)
        for nome in self.nomes:
            if nome in texto_norm:
                return True, nome
        return False, None


class BotPublicacoesJaloma:
    def __init__(self, config_path="config_jaloma.json"):
        print("Iniciando Bot de Publicacoes - modo Jaloma")
        print("=" * 60)

        with open(config_path, "r", encoding="utf-8") as file:
            self.config = json.load(file)

        print("\nConectando ao email...")
        self.email_processor = EmailProcessor(self.config["email"])

        provedor = self.config.get("ia", {}).get("provedor", "ollama")
        print(f"\nConectando a IA ({provedor.upper()})...")
        self.llm_processor = LLMProcessor(self.config["ia"])

        print("\nConectando ao Jaloma...")
        self.jaloma_manager = JalomaManager(self.config["jaloma"])

        print("\nCarregando lista especial...")
        self.lista_especial = ListaEspecial(self.config.get("lista_especial", {}))

        print("\n" + "=" * 60)
        print("Bot Jaloma inicializado com sucesso")
        print(f"Provedor de IA: {self.llm_processor.get_provedor_info()}")
        print("=" * 60 + "\n")

        self.emails_processados = set()
        self.ignorados_lista_especial = 0

    def processar_publicacao(self, pub_data):
        try:
            numero_pub = pub_data.get("numero_publicacao", 1)
            total_pub = pub_data.get("total_publicacoes", 1)

            print(f"\n{'-' * 50}")
            print(f"Processando publicacao {numero_pub}/{total_pub}...")
            print(f"{'-' * 50}")

            esta_na_lista, nome_encontrado = self.lista_especial.verificar(pub_data["corpo"])
            if esta_na_lista:
                detalhe = f"IGNORADO | lista especial | {nome_encontrado}"
                print(detalhe)
                self.ignorados_lista_especial += 1
                self.emails_processados.add(pub_data["id"])
                return {"status": "ignorado", "detalhe": detalhe}

            print(f"Analisando com IA ({self.llm_processor.get_provedor_info()})...")
            dados_extraidos = self.llm_processor.extrair_dados(pub_data["corpo"])
            if not dados_extraidos:
                return {"status": "falha", "erro": "IA nao retornou dados validos"}

            processo = dados_extraidos.get("numero_processo") or "N/A"
            cliente = dados_extraidos.get("cliente") or "N/A"
            tipo = dados_extraidos.get("tipo_ato") or "N/A"
            prazo = dados_extraidos.get("prazo_calculado") or "N/A"

            print("Dados extraidos:")
            print(f"  Processo: {processo}")
            print(f"  Cliente: {str(cliente)[:60]}")
            print(f"  Tipo: {tipo}")
            print(f"  Prazo (PF): {prazo}")

            resultado = self.jaloma_manager.criar_ou_reaproveitar_card(dados_extraidos, pub_data)
            self.emails_processados.add(pub_data["id"])

            status = "criado" if resultado["criado"] else "existente"
            detalhe = f"{status.upper()} | {processo} | {str(cliente)[:40]} | PF {prazo}"
            print(detalhe)
            return {"status": status, "detalhe": detalhe, "card": resultado}

        except Exception as exc:
            erro = f"Falha ao processar publicacao: {exc}"
            print(erro)
            return {"status": "falha", "erro": erro}

    def _marcar_emails(self):
        if not self.config["email"].get("marcar_como_lido_apos_processar", False):
            return

        print(f"\nMarcando {len(self.emails_processados)} email(s) como lido(s)...")
        for email_id in self.emails_processados:
            try:
                self.email_processor.marcar_email_como_lido(email_id)
            except Exception as exc:
                print(f"Aviso: erro ao marcar email {email_id}: {exc}")
        self.emails_processados.clear()

    def executar_uma_vez(self):
        print("\n" + "=" * 60)
        print("VERIFICANDO EMAILS NOVOS...")
        print("=" * 60)

        self.ignorados_lista_especial = 0
        publicacoes = self.email_processor.buscar_emails_novos(
            dias=self.config["processamento"].get("dias_verificar", 7)
        )

        if not publicacoes:
            print("\nNenhuma publicacao nova encontrada.")
            return

        print(f"\n{len(publicacoes)} publicacao(oes) encontrada(s).")

        criados = 0
        existentes = 0
        falhas = 0
        detalhes = []
        erros = []

        for indice, pub_data in enumerate(publicacoes, 1):
            print(f"\n{'=' * 60}")
            print(f"Processando {indice}/{len(publicacoes)}")
            print(f"{'=' * 60}")

            resultado = self.processar_publicacao(pub_data)
            status = resultado["status"]

            if status == "criado":
                criados += 1
                detalhes.append(resultado["detalhe"])
            elif status == "existente":
                existentes += 1
                detalhes.append(resultado["detalhe"])
            elif status == "ignorado":
                detalhes.append(resultado["detalhe"])
            else:
                falhas += 1
                erros.append(resultado.get("erro", "Falha sem detalhe"))

            if indice < len(publicacoes):
                print("\nAguardando 3 segundos...")
                time.sleep(3)

        self._marcar_emails()

        resumo = {
            "total": len(publicacoes),
            "criados": criados,
            "existentes": existentes,
            "ignorados": self.ignorados_lista_especial,
            "falhas": falhas,
            "detalhes": detalhes,
            "erros": erros,
        }

        try:
            card_resumo = self.jaloma_manager.criar_card_resumo(resumo)
            print(f"\nCard de resumo criado: {card_resumo.get('processo')}")
        except Exception as exc:
            print(f"\nAviso: nao foi possivel criar o card de resumo: {exc}")

        print(f"\n{'=' * 60}")
        print("RESUMO DO PROCESSAMENTO")
        print(f"{'=' * 60}")
        print(f"Total de publicacoes: {len(publicacoes)}")
        print(f"Cards criados: {criados}")
        print(f"Cards ja existentes: {existentes}")
        print(f"Ignorados (lista especial): {self.ignorados_lista_especial}")
        print(f"Falhas: {falhas}")
        print(f"{'=' * 60}\n")

    def executar_continuo(self):
        intervalo = self.config["processamento"].get("intervalo_minutos", 15)

        print("\n" + "=" * 60)
        print("MODO CONTINUO ATIVADO - JALOMA")
        print("=" * 60)
        print(f"Intervalo: {intervalo} minuto(s)")
        print("Pressione Ctrl+C para parar")
        print("=" * 60 + "\n")

        try:
            while True:
                hora_atual = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{hora_atual}] Iniciando verificacao...")

                try:
                    self.executar_uma_vez()
                except Exception as exc:
                    print(f"Erro durante execucao: {exc}")

                proxima = datetime.now().timestamp() + (intervalo * 60)
                print(f"Aguardando {intervalo} minuto(s)...")
                print(f"Proxima verificacao em: {datetime.fromtimestamp(proxima).strftime('%H:%M:%S')}")
                time.sleep(intervalo * 60)
        except KeyboardInterrupt:
            print("\n\nBot interrompido pelo usuario.")
            print("Ate logo.\n")


def main():
    print("\n" + "=" * 60)
    print("BOT DE PUBLICACOES JURIDICAS - MODO JALOMA")
    print("Versao 1.0")
    print("=" * 60 + "\n")

    config_path = Path("config_jaloma.json")
    if not config_path.exists():
        print("Arquivo config_jaloma.json nao encontrado.")
        print("\nCampos necessarios:")
        print("  - email: servidor, porta, usuario, senha, label")
        print("  - ia: provedor ('ollama' ou 'gemini'), ollama, gemini")
        print("  - jaloma: supabase_url, supabase_key, responsavel_padrao")
        print("  - lista_especial: arquivo")
        input("\nPressione ENTER para sair...")
        sys.exit(1)

    try:
        bot = BotPublicacoesJaloma(str(config_path))
    except Exception as exc:
        print(f"Erro ao inicializar bot: {exc}")
        import traceback
        traceback.print_exc()
        input("\nPressione ENTER para sair...")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--continuo":
        bot.executar_continuo()
    else:
        bot.executar_uma_vez()
        input("\nProcessamento concluido. Pressione ENTER para sair...")


if __name__ == "__main__":
    main()
