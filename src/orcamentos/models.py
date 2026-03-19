from django.conf import settings
from django.db import models
from django.utils import timezone

STATUS_CHOICE = [
    ("Não Enviado", "Não Enviado"),
    ("Aguardando Aprovação", "Aguardando Aprovação"),
    ("Aprovado", "Aprovado"),
    ("Reprogramado", "Reprogramado"),
    ("Cancelado", "Cancelado"),
    ("Concluído", "Concluído"),
    ("Desativado", "Desativado"),
]


class Orcamento(models.Model):
    # Rev0 => orcamento_original = NULL
    # Revisões => apontam para Rev0
    orcamento_original = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="revisoes",
    )

    numero_orcamento = models.CharField(max_length=40, null=True, blank=True)
    revisao = models.PositiveIntegerField(default=0)

    is_revisao = models.BooleanField(default=False)
    is_ativo = models.BooleanField(default=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICE, default="Não Enviado")

    enviado = models.BooleanField(default=False)
    aprovado = models.BooleanField(default=False)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orcamentos_aprovados",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["orcamento_original", "revisao"]),
            models.Index(fields=["orcamento_original", "is_ativo"]),
            models.Index(fields=["status"]),
        ]

    @property
    def original(self):
        return self.orcamento_original or self

    def __str__(self):
        return self.numero_orcamento or f"Orçamento #{self.pk}"

    def pode_transicionar_para(self, novo_status: str) -> bool:
        """
        Regras MVP (ajustáveis):
        - Não Enviado -> Aguardando Aprovação
        - Aguardando Aprovação -> Aprovado | Reprogramado | Cancelado
        - Aprovado -> Concluído | Reprogramado | Desativado
        - Reprogramado -> Aguardando Aprovação | Cancelado
        - Cancelado/Concluído/Desativado: finais (exceto Desativado sempre bloqueia)
        """
        atual = self.status

        if atual == "Desativado":
            return False

        finais = {"Cancelado", "Concluído"}
        if atual in finais:
            return False

        if novo_status == "Aguardando Aprovação":
            return atual in {"Não Enviado", "Reprogramado"}
        if novo_status == "Aprovado":
            return atual == "Aguardando Aprovação"
        if novo_status == "Concluído":
            return atual == "Aprovado"
        if novo_status == "Reprogramado":
            return atual in {"Aguardando Aprovação", "Aprovado"}
        if novo_status == "Cancelado":
            return atual in {"Não Enviado", "Aguardando Aprovação", "Reprogramado"}
        if novo_status == "Desativado":
            return True

        return False


class OrcamentoHistorico(models.Model):
    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name="historico")
    acao = models.CharField(max_length=60)  # e.g. CRIAR_REVISAO, MUDAR_STATUS
    status_de = models.CharField(max_length=30, null=True, blank=True)
    status_para = models.CharField(max_length=30, null=True, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orcamento_logs",
    )
    observacao = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]