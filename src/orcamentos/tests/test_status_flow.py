import pytest
from django.contrib.auth import get_user_model
from orcamentos.models import Orcamento
from orcamentos.services import mudar_status

User = get_user_model()

@pytest.mark.django_db
def test_fluxo_aprovacao():
    u = User.objects.create(username="approver")

    o = Orcamento.objects.create(numero_orcamento="00524-26", status="Não Enviado", is_ativo=True)

    o = mudar_status(o.id, "Aguardando Aprovação", actor=u)
    assert o.status == "Aguardando Aprovação"
    assert o.enviado is True
    assert o.aprovado is False

    o = mudar_status(o.id, "Aprovado", actor=u)
    assert o.status == "Aprovado"
    assert o.aprovado is True
    assert o.aprovado_por == u
    assert o.data_aprovacao is not None


@pytest.mark.django_db
def test_transicao_invalida_gera_erro():
    u = User.objects.create(username="u")
    o = Orcamento.objects.create(status="Não Enviado")

    with pytest.raises(ValueError):
        mudar_status(o.id, "Aprovado", actor=u)  # não pode pular a aprovação