"""
Integracao do bot de publicacoes com o JalomaPrazos via Supabase REST.
"""

import hashlib
import re
from datetime import datetime

import requests


def texto_limpo(valor):
    return str(valor or "").strip()


def resumir_texto(valor, limite=180):
    texto = re.sub(r"\s+", " ", texto_limpo(valor))
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3].rstrip() + "..."


def normalizar_publicacao(texto):
    return re.sub(r"\s+", " ", texto_limpo(texto)).lower()


class JalomaManager:
    def __init__(self, config):
        self.supabase_url = texto_limpo(config.get("supabase_url")).rstrip("/")
        self.supabase_key = texto_limpo(config.get("supabase_key"))
        self.responsavel_padrao = texto_limpo(config.get("responsavel_padrao")) or "Raphael"
        self.lista_manual_entrada = texto_limpo(config.get("lista_manual_entrada")) or "Entrada Bot"
        self.modulo = texto_limpo(config.get("modulo")) or "prazos"
        self.mostrar_na_semana = bool(config.get("mostrar_na_semana", False))
        self.timeout = int(config.get("timeout_segundos", 20))

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("jaloma.supabase_url e jaloma.supabase_key sao obrigatorios")

        self.base_url = f"{self.supabase_url}/rest/v1"
        self._garantir_lista_manual()

    def _headers(self, prefer=None):
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(self, method, endpoint, *, params=None, json_data=None, prefer=None, allow_empty=False):
        response = requests.request(
            method,
            f"{self.base_url}/{endpoint.lstrip('/')}",
            headers=self._headers(prefer),
            params=params,
            json=json_data,
            timeout=self.timeout,
        )

        if response.status_code >= 400:
            detalhe = response.text[:500] if response.text else response.reason
            raise RuntimeError(f"Supabase retornou {response.status_code}: {detalhe}")

        if not response.text.strip():
            return None if allow_empty else []

        return response.json()

    def _garantir_lista_manual(self):
        listas = self._request(
            "GET",
            "listas_clientes",
            params={
                "select": "id,nome,responsavel",
                "responsavel": f"eq.{self.responsavel_padrao}",
            },
        )

        nome_normalizado = self.lista_manual_entrada.lower()
        for lista in listas:
            if texto_limpo(lista.get("nome")).lower() == nome_normalizado:
                return lista

        criada = self._request(
            "POST",
            "listas_clientes",
            json_data={
                "nome": self.lista_manual_entrada,
                "aliases": [],
                "responsavel": self.responsavel_padrao,
            },
            prefer="return=representation",
        )
        return criada[0] if criada else None

    def _hash_publicacao(self, email_data):
        corpo = normalizar_publicacao(email_data.get("corpo"))
        digest = hashlib.sha1(corpo.encode("utf-8")).hexdigest()
        return f"botpub:{digest}"

    def _hash_execucao(self):
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        digest = hashlib.sha1(stamp.encode("utf-8")).hexdigest()[:12]
        return f"botrun:{stamp}:{digest}"

    def _para_iso(self, data_br):
        valor = texto_limpo(data_br)
        if not valor:
            return None

        try:
            dia, mes, ano = valor.split("/")
            return f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"
        except ValueError:
            return None

    def _observacao_card(self, dados, email_data):
        texto_publicacao = texto_limpo(email_data.get("corpo"))
        if len(texto_publicacao) > 12000:
            texto_publicacao = texto_publicacao[:12000].rstrip() + "\n\n... (Texto truncado)"

        topicos = dados.get("resumo_topicos") or []
        linhas_topicos = "\n".join(f"- {resumir_texto(topico, 220)}" for topico in topicos[:6])
        prazo_mencionado = texto_limpo(dados.get("prazo_mencionado"))
        observacoes = texto_limpo(dados.get("observacoes"))
        confianca = int(float(dados.get("confianca", 0.0)) * 100)

        blocos = [
            "🤖 [BOT PUBLICACOES]",
            "⚠️ Revisar prazo calculado e conferir o texto original.",
            "",
            "=" * 50,
            "🧾 TEXTO DA PUBLICACAO",
            "=" * 50,
            "",
            texto_publicacao or "Texto nao disponivel.",
            "",
            "=" * 50,
            "🤖 RESUMO AUTOMATICO",
            "=" * 50,
            "",
            f"Processo: {texto_limpo(dados.get('numero_processo')) or 'N/A'}",
            f"Cliente: {texto_limpo(dados.get('cliente')) or 'N/A'}",
            f"Tipo: {texto_limpo(dados.get('tipo_ato')) or 'N/A'}",
            f"Tribunal: {texto_limpo(dados.get('tribunal')) or 'N/A'}",
            f"Vara: {texto_limpo(dados.get('vara')) or 'N/A'}",
            f"📅 Prazo calculado: {texto_limpo(dados.get('prazo_calculado')) or 'N/A'}",
            f"Prazo mencionado: {prazo_mencionado or 'Nao identificado'}",
            f"Prazo implicito: {'Sim' if dados.get('prazo_implicito') else 'Nao'}",
            f"Urgente: {'Sim' if dados.get('urgente') else 'Nao'}",
            f"Confianca da IA: {confianca}%",
        ]

        if linhas_topicos:
            blocos.extend([
                "",
                "📋 DETERMINACOES:",
                linhas_topicos,
            ])

        if observacoes:
            blocos.extend([
                "",
                "⚠️ OBSERVACOES:",
                observacoes,
            ])

        blocos.extend([
            "",
            "=" * 50,
            "⚠️ ATENCAO",
            "=" * 50,
            "Resumo gerado pelo bot. Sempre conferir a publicacao original.",
            f"Processado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ])

        return "\n".join(blocos).strip()

    def _demanda_resumo(self, dados):
        topicos = dados.get("resumo_topicos") or []
        if topicos:
            return f"[BOT] {resumir_texto(topicos[0], 160)}"

        tipo_ato = texto_limpo(dados.get("tipo_ato")) or "Publicacao juridica"
        prazo = texto_limpo(dados.get("prazo_calculado")) or "sem prazo calculado"
        return f"[BOT] {tipo_ato} - revisar prazo {prazo}"

    def _montar_registro_publicacao(self, dados, email_data):
        prazo_fatal = self._para_iso(dados.get("prazo_calculado"))
        if not prazo_fatal:
            prazo_fatal = datetime.now().strftime("%Y-%m-%d")

        return {
            "processo": texto_limpo(dados.get("numero_processo")) or "SEM NUMERO",
            "pasta": None,
            "cliente": texto_limpo(dados.get("cliente")) or None,
            "contrario": None,
            "tipo_prazo": texto_limpo(dados.get("tipo_ato")) or "Publicacao",
            "demanda": self._demanda_resumo(dados),
            "prazo_fatal": prazo_fatal,
            "data_entrada": self._para_iso(dados.get("data_publicacao")),
            "dia_semana": None,
            "responsavel": self.responsavel_padrao,
            "kanban_grupo": None,
            "urgente": bool(dados.get("urgente")),
            "mostrar_na_semana": self.mostrar_na_semana,
            "lista_cliente_manual": self.lista_manual_entrada,
            "observacao": self._observacao_card(dados, email_data),
            "origem": "manual",
            "modulo": self.modulo,
            "status": "pendente",
            "excel_hash": self._hash_publicacao(email_data),
        }

    def _buscar_card_existente(self, hash_externo):
        cards = self._request(
            "GET",
            "cards",
            params={
                "select": "id,processo,cliente,prazo_fatal,excel_hash",
                "excel_hash": f"eq.{hash_externo}",
            },
        )
        return cards[0] if cards else None

    def criar_ou_reaproveitar_card(self, dados, email_data):
        registro = self._montar_registro_publicacao(dados, email_data)
        existente = self._buscar_card_existente(registro["excel_hash"])

        if existente:
            return {
                "id": existente["id"],
                "titulo": existente.get("processo") or registro["processo"],
                "criado": False,
                "registro": existente,
            }

        criado = self._request(
            "POST",
            "cards",
            json_data=registro,
            prefer="return=representation",
        )
        card = criado[0]
        return {
            "id": card["id"],
            "titulo": card.get("processo") or registro["processo"],
            "criado": True,
            "registro": card,
        }

    def _observacao_resumo(self, resumo_execucao):
        linhas = [
            "🤖 [BOT PUBLICACOES]",
            "Resumo da ultima execucao do bot Jaloma.",
            "",
            f"Horario: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"Total de publicacoes vistas: {resumo_execucao['total']}",
            f"Cards criados: {resumo_execucao['criados']}",
            f"Cards ja existentes: {resumo_execucao['existentes']}",
            f"Ignorados pela lista especial: {resumo_execucao['ignorados']}",
            f"Falhas: {resumo_execucao['falhas']}",
        ]

        detalhes = resumo_execucao.get("detalhes") or []
        if detalhes:
            linhas.extend(["", "📋 DETALHES:"])
            for detalhe in detalhes:
                linhas.append(f"- {detalhe}")

        erros = resumo_execucao.get("erros") or []
        if erros:
            linhas.extend(["", "⚠️ ERROS:"])
            for erro in erros:
                linhas.append(f"- {erro}")

        return "\n".join(linhas).strip()

    def criar_card_resumo(self, resumo_execucao):
        hoje = datetime.now().strftime("%Y-%m-%d")
        registro = {
            "processo": f"RESUMO BOT {datetime.now().strftime('%d/%m %H:%M')}",
            "pasta": None,
            "cliente": "Sistema",
            "contrario": None,
            "tipo_prazo": "Resumo do bot",
            "demanda": (
                f"[BOT] {resumo_execucao['criados']} criado(s), "
                f"{resumo_execucao['existentes']} existente(s), "
                f"{resumo_execucao['ignorados']} ignorado(s), "
                f"{resumo_execucao['falhas']} falha(s)"
            ),
            "prazo_fatal": hoje,
            "data_entrada": hoje,
            "dia_semana": None,
            "responsavel": self.responsavel_padrao,
            "kanban_grupo": None,
            "urgente": False,
            "mostrar_na_semana": False,
            "lista_cliente_manual": self.lista_manual_entrada,
            "observacao": self._observacao_resumo(resumo_execucao),
            "origem": "manual",
            "modulo": self.modulo,
            "status": "pendente",
            "excel_hash": self._hash_execucao(),
        }

        criado = self._request(
            "POST",
            "cards",
            json_data=registro,
            prefer="return=representation",
        )
        return criado[0]
