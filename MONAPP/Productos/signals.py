from django.db.models.signals import post_save,post_delete
from django.dispatch import receiver
from .models import Producto
from inventario.models import Stock

@receiver(post_save,sender=Producto)
def crar_stock_producto(sender,instance,created,*args,**kwargs):
    if created:
        Stock.objects.create(producto=instance)