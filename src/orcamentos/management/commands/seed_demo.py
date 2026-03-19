from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from orcamentos.models import Orcamento
from orcamentos.services import criar_revisao, mudar_status

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data for EstimateFlow (idempotent + cleanup duplicates)"

    @transaction.atomic
    def handle(self, *args, **options):
        # ---------------------------------------------------------------------
        # User
        # ---------------------------------------------------------------------
        user, _ = User.objects.get_or_create(username="demo")
        user.set_password("demo1234")
        user.is_staff = True
        user.is_superuser = True
        user.save()

        def ensure_rev0(numero: str, status: str) -> Orcamento:
            """
            Ensure a single Rev0 exists for this numero.
            If duplicates exist, keep the oldest and delete the rest (demo DB).
            """
            qs = Orcamento.objects.filter(numero_orcamento=numero, revisao=0).order_by("id")
            if qs.exists():
                o0 = qs.first()
                # delete duplicates
                dup_ids = list(qs.values_list("id", flat=True))[1:]
                if dup_ids:
                    Orcamento.objects.filter(id__in=dup_ids).delete()

                # normalize Rev0 fields
                if o0.orcamento_original_id is not None:
                    o0.orcamento_original = None
                o0.is_revisao = False
                o0.is_ativo = True  # start as active (services may toggle later)
                o0.status = status
                o0.save()
                return o0

            # create fresh Rev0
            o0 = Orcamento.objects.create(
                numero_orcamento=numero,
                revisao=0,
                is_revisao=False,
                is_ativo=True,
                status=status,
            )
            # Rev0 root
            o0.orcamento_original = None
            o0.save(update_fields=["orcamento_original"])
            return o0

        # ---------------------------------------------------------------------
        # Group A: Not sent
        # ---------------------------------------------------------------------
        o0_a = ensure_rev0("00524-26", "Não Enviado")

        # ---------------------------------------------------------------------
        # Group B: Waiting approval
        # ---------------------------------------------------------------------
        o0_b = ensure_rev0("00999-26", "Não Enviado")
        if o0_b.status != "Aguardando Aprovação":
            mudar_status(o0_b.id, "Aguardando Aprovação", actor=user, observacao="Seed: sent for approval")

        # ---------------------------------------------------------------------
        # Group C: Approved + Rev1 (post-approval)
        # ---------------------------------------------------------------------
        o0_c = ensure_rev0("01000-26", "Não Enviado")
        if o0_c.status != "Aprovado":
            if o0_c.status != "Aguardando Aprovação":
                mudar_status(o0_c.id, "Aguardando Aprovação", actor=user, observacao="Seed: sent for approval")
            mudar_status(o0_c.id, "Aprovado", actor=user, observacao="Seed: approved")

        # Ensure Rev1 exists for group C
        has_rev1 = Orcamento.objects.filter(orcamento_original=o0_c, revisao=1).exists()
        if not has_rev1:
            criar_revisao(o0_c.id, actor=user, manter_aprovacao=True)

        self.stdout.write(self.style.SUCCESS("✅ Seed complete"))
        self.stdout.write(self.style.SUCCESS("Login: demo / demo1234"))
        self.stdout.write("Groups ready:")
        self.stdout.write(" - 00524-26 (Não Enviado)")
        self.stdout.write(" - 00999-26 (Aguardando Aprovação)")
        self.stdout.write(" - 01000-26 (Aprovado) + Rev1 (post-approval)")