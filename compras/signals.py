"""Compras signals.

El stock se gestiona de forma transaccional en `compras.services` e
`inventario.services`. Este modulo queda intencionalmente sin receivers para
evitar recalculos historicos que desalineen `inventario.Stock`.
"""

