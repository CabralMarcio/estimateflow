from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Orcamento
from .services import criar_revisao, mudar_status


@login_required
def orcamento_list(request):
    qs = Orcamento.objects.all().select_related("aprovado_por", "orcamento_original")

    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    ativo = request.GET.get("ativo")
    if ativo in {"0", "1"}:
        qs = qs.filter(is_ativo=(ativo == "1"))

    qs = qs.order_by("-updated_at")[:200]
    return render(request, "orcamentos/list.html", {"orcamentos": qs})


@login_required
def grupo_detail(request, original_id):
    original = get_object_or_404(Orcamento, pk=original_id)
    base = original.original
    revisoes = (
        Orcamento.objects.filter(orcamento_original=base)
        .select_related("aprovado_por")
        .order_by("revisao", "id")
    )
    return render(request, "orcamentos/grupo_detail.html", {"original": base, "revisoes": revisoes})


@login_required
def htmx_actions_panel(request, orcamento_id):
    o = get_object_or_404(Orcamento, pk=orcamento_id)
    return render(request, "orcamentos/partials/actions_panel.html", {"o": o})


@login_required
@require_POST
def htmx_criar_revisao(request, orcamento_id):
    manter = request.POST.get("manter_aprovacao") == "1"
    nova = criar_revisao(orcamento_id, actor=request.user, manter_aprovacao=manter)
    return render(request, "orcamentos/partials/revisao_created.html", {"nova": nova})


@login_required
@require_POST
def htmx_mudar_status(request, orcamento_id):
    novo_status = request.POST.get("status")
    if not novo_status:
        return HttpResponseBadRequest("status required")

    try:
        o = mudar_status(orcamento_id, novo_status, actor=request.user, observacao=request.POST.get("obs", ""))
    except ValueError as e:
        return render(request, "orcamentos/partials/error.html", {"message": str(e)})

    return render(request, "orcamentos/partials/status_badge.html", {"o": o})