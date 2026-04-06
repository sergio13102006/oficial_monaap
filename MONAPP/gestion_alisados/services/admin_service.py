from clientes.models import Cliente
from promociones.models import Promocion

from ..forms import GestionAlisadoForm
from .persistence_service import get_last_gestion_values


def _promociones_activas():
    return Promocion.objects.filter(activa=True).order_by("nombre")


def build_modal_capture_context(cliente_id="", desde_clientes=False):
    cliente_obj = None
    cliente_bloqueado = False

    if cliente_id:
        try:
            cliente_obj = Cliente.objects.get(id=int(cliente_id))
        except (ValueError, Cliente.DoesNotExist):
            cliente_obj = None

    form = GestionAlisadoForm(initial=get_last_gestion_values(cliente_obj) if cliente_obj else None)
    form.fields["cliente"].widget.attrs["id"] = "selectCliente"
    form.fields["cliente"].widget.attrs["class"] = "form-select"

    if cliente_obj and desde_clientes:
        form.fields["cliente"].widget.attrs["disabled"] = "disabled"
        cliente_bloqueado = True

    return {
        "form": form,
        "is_modal": True,
        "cliente_preseleccionado": cliente_obj,
        "cliente_bloqueado": cliente_bloqueado,
        "cliente_id_bloqueado": cliente_obj.id if cliente_obj and cliente_bloqueado else "",
        "desde_clientes": desde_clientes,
        "promociones_activas": _promociones_activas(),
    }


def build_admin_capture_context(form, is_modal=False, action_url=""):
    return {
        "form": form,
        "titulo": "Gestion de Alisado",
        "is_modal": is_modal,
        "action_url": action_url,
        "promociones_activas": _promociones_activas(),
    }
