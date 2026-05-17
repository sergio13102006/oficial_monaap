from django.db.models import Q
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
import csv
from core.global_ordenamiento import apply_smart_sorting, sorting_context
from .models import Stock


def inventario_lista(request):
    q = request.GET.get("q", "").strip()
    estado_stock = request.GET.get("estado_stock", "").strip()

    stock = Stock.objects.select_related("producto").all()

    if q:
        stock = stock.filter(
            Q(producto__nombre__icontains=q) |
            Q(producto__codigo__icontains=q)
        )
    #filtro de nivel stock y rango
    if estado_stock == "bajo":
        stock = stock.filter(cantidad_actual__lte=10)
    elif estado_stock == "normal":
        stock = stock.filter(cantidad_actual__gt=10, cantidad_actual__lte=20)
    elif estado_stock=="alto":
        stock = stock.filter(cantidad_actual__gt=20)
     #para stock alto rodenar de mayor a menor    
    if estado_stock == "alto":
        stock = stock.order_by("-cantidad_actual","producto__nombre")
        sort_key = "stock"
        direction = "desc"
    else:
        
        stock, sort_key, direction = apply_smart_sorting(
            request,
            stock,
            default_sort="producto__nombre",
            default_dir="asc",
            aliases={
                "producto": "producto__nombre",
                "unidad": "producto__unidad_medida",
                "stock": "cantidad_actual",
                "actualizacion": "actualizado_en",
            }
        )

    return render(request, "inventario/inventario.html", {
        "stock": stock,
        "q": q,
        "estado_stock": estado_stock,
        **sorting_context(sort_key, direction),
    })


@login_required
def reporte_stock_csv(request):
    q = request.GET.get("q", "").strip()
    estado_stock = request.GET.get("estado_stock", "").strip()

    stock = Stock.objects.select_related("producto").all()

    if q:
        stock = stock.filter(
            Q(producto__nombre__icontains=q) |
            Q(producto__codigo__icontains=q)
        )

    if estado_stock == "bajo":
        stock = stock.filter(cantidad_actual__lte=10)
    elif estado_stock == "normal":
        stock = stock.filter(cantidad_actual__gt=10, cantidad_actual__lte=20)
    elif estado_stock == "alto":
        stock = stock.filter(cantidad_actual__gt=20)

    stock = stock.order_by("producto__nombre")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="reporte_stock_inventario.csv"'
    response.write("\ufeff")

    writer = csv.writer(response)
    writer.writerow(["Codigo", "Producto", "Unidad", "Stock actual", "Ultima actualizacion"])

    for s in stock:
        writer.writerow([
            s.producto.codigo,
            s.producto.nombre,
            s.producto.get_unidad_medida_display(),
            s.cantidad_actual,
            s.actualizado_en.strftime("%d/%m/%Y %H:%M"),
        ])

    return response
