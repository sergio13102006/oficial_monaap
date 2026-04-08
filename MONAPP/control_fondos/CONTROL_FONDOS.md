# Control de Fondos

## Reglas funcionales congeladas

- No es un módulo de pagos. Es un módulo de control de fondos.
- Vive en `control_fondos` y recibe movimientos desde compras y servicios.
- Las cuentas financieras son parametrizables; no se limitan a caja o banco.
- La base del día se carga manualmente por cuenta.
- La jornada cambia por fecha y las anteriores se cierran automáticamente.
- No se permiten movimientos sobre una cuenta sin base del día.
- Las compras restan fondos.
- Los servicios solo suman fondos cuando el cobro real ya ocurrió.
- Los movimientos aplicados no se eliminan físicamente.
- Las correcciones se hacen con reversa o anulación lógica vinculada al movimiento original.
- Los flujos críticos deben ser idempotentes para evitar duplicados por reintentos.

## Estados

### JornadaDiaria

- `ABIERTA`
- `CERRADA_AUTO`

### MovimientoCuenta.tipo

- `ENTRADA`
- `SALIDA`

### MovimientoCuenta.clase

- `SERVICIO`
- `COMPRA`
- `AJUSTE`
- `TRANSFERENCIA`
- `ANULACION`
- `REVERSA`

### MovimientoCuenta.estado

- `ACTIVO`
- `ANULADO`
