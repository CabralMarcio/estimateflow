import copy
import re
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from .models import Orcamento, OrcamentoHistorico


def _log(orcamento: Orcamento, acao: str, actor=None, status_de=None, status_para=None, observacao=""):
    OrcamentoHistorico.objects.create(
        orcamento=orcamento,
        acao=acao,
        actor=actor,
        status_de=status_de,
        status_para=status_para,
        observacao=observacao,
    )


@transaction.atomic
def criar_revisao(orcamento_id: int, actor=None, form_data=None, manter_aprovacao: bool = False) -> Orcamento:
    atual = Orcamento.objects.select_for_update().get(pk=orcamento_id)
    original = atual.original

    ultima = Orcamento.objects.filter(orcamento_original=original).order_by("-revisao").first()
    nova_rev_num = 1 if not ultima else (ultima.revisao or 0) + 1

    # Desativa o ativo atual do grupo (inclui o original Rev0 e as revisões)
    Orcamento.objects.filter(
        Q(pk=original.pk) | Q(orcamento_original=original),
        is_ativo=True
    ).update(is_ativo=False)

    nova = copy.copy(atual)
    nova.pk = None
    nova.revisao = nova_rev_num
    nova.is_revisao = True
    nova.is_ativo = True
    nova.orcamento_original = original

    num = (atual.numero_orcamento or "").strip()
    if num:
        base_num = re.sub(r"-Rev\.?\d+$", "", num, flags=re.IGNORECASE)
        nova.numero_orcamento = f"{base_num}-Rev{nova.revisao}"
    else:
        nova.numero_orcamento = None

    if manter_aprovacao:
        nova.status = "Aprovado"
        nova.aprovado = True
        nova.enviado = True
        log_acao = "CRIAR_REVISAO_POS_APROVACAO"
        log_obs = "Revision created keeping approval."
    else:
        nova.status = "Não Enviado"
        nova.aprovado = False
        nova.enviado = False
        nova.data_aprovacao = None
        nova.aprovado_por = None
        log_acao = "CRIAR_REVISAO"
        log_obs = "Revision created for rework/resend."

    if form_data:
        campos_ignorar = {
            "numero_orcamento", "is_ativo", "is_revisao", "orcamento_original",
            "aprovado", "enviado", "data_aprovacao", "aprovado_por", "revisao", "status",
        }
        for key, value in form_data.items():
            if key in campos_ignorar:
                continue
            if hasattr(nova, key):
                setattr(nova, key, value)

    nova.save()
    _log(nova, log_acao, actor=actor, observacao=log_obs)
    return nova

@transaction.atomic
def mudar_status(orcamento_id: int, novo_status: str, actor=None, observacao="") -> Orcamento:
    o = Orcamento.objects.select_for_update().get(pk=orcamento_id)

    if not o.pode_transicionar_para(novo_status):
        raise ValueError(f"Transição inválida: {o.status} -> {novo_status}")

    status_antigo = o.status
    o.status = novo_status

    if novo_status == "Aguardando Aprovação":
        o.enviado = True
        o.aprovado = False
        o.data_aprovacao = None
        o.aprovado_por = None

    if novo_status == "Aprovado":
        o.aprovado = True
        o.data_aprovacao = timezone.now()
        o.aprovado_por = actor

    if novo_status in {"Cancelado", "Desativado", "Concluído"}:
        o.is_ativo = False

    o.save()
    _log(o, "MUDAR_STATUS", actor=actor, status_de=status_antigo, status_para=novo_status, observacao=observacao)
    return o