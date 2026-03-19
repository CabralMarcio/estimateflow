import pytest
from django.contrib.auth import get_user_model
from orcamentos.models import Orcamento
from orcamentos.services import criar_revisao

User = get_user_model()

@pytest.mark.django_db
def test_criar_revisao_desativa_ativo_anterior():
    u = User.objects.create(username="u1")

    rev0 = Orcamento.objects.create(numero_orcamento="00524-26", status="Aprovado", aprovado=True, enviado=True)
    # rev0 é o original do grupo
    rev1 = criar_revisao(rev0.id, actor=u, manter_aprovacao=False)

    rev0.refresh_from_db()
    rev1.refresh_from_db()

    assert rev0.is_ativo is False
    assert rev1.is_ativo is True
    assert rev1.revisao == 1
    assert rev1.status == "Não Enviado"
    assert rev1.numero_orcamento.endswith("-Rev1")


@pytest.mark.django_db
def test_criar_revisao_pos_aprovacao_mantem_aprovacao():
    u = User.objects.create(username="u1")

    rev0 = Orcamento.objects.create(
        numero_orcamento="00524-26",
        status="Aprovado",
        aprovado=True,
        enviado=True,
        data_aprovacao="2026-01-01T00:00:00Z",
        aprovado_por=u,
    )

    rev1 = criar_revisao(rev0.id, actor=u, manter_aprovacao=True)
    rev1.refresh_from_db()

    assert rev1.status == "Aprovado"
    assert rev1.aprovado is True
    assert rev1.enviado is True
    assert rev1.aprovado_por == u