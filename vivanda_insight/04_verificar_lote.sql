-- Verifica el lote demo en PostgreSQL después de generarlo.

SELECT
    p.sku,
    p.nombre AS producto,
    COUNT(DISTINCT v.id_venta) AS ventas,
    SUM(dv.cantidad) AS unidades_vendidas,
    SUM(dv.precio_unitario * dv.cantidad - COALESCE(dv.descuento, 0))
        AS monto_neto
FROM public.pago AS pago
JOIN public.venta AS v
    ON v.id_venta = pago.id_venta
JOIN public.detalle_venta AS dv
    ON dv.id_venta = v.id_venta
JOIN public.producto AS p
    ON p.id_producto = dv.id_producto
WHERE pago.referencia LIKE 'VIVANDA-EXPO-4PROD-%'
GROUP BY p.sku, p.nombre
ORDER BY p.nombre;

SELECT
    p.sku,
    p.nombre AS producto,
    a.nombre AS almacen,
    i.stock_actual,
    i.stock_minimo,
    i.actualizado_en,
    COUNT(m.id_movimiento) AS salidas_demo,
    COALESCE(SUM(m.cantidad), 0) AS unidades_descontadas
FROM public.movimiento_inventario AS m
JOIN public.inventario AS i
    ON i.id_almacen = m.id_almacen
   AND i.id_producto = m.id_producto
JOIN public.almacen AS a
    ON a.id_almacen = i.id_almacen
JOIN public.producto AS p
    ON p.id_producto = i.id_producto
WHERE m.observacion = 'VIVANDA-EXPO-4PROD'
  AND m.tipo = 'SALIDA'
GROUP BY p.sku, p.nombre, a.nombre, i.stock_actual, i.stock_minimo, i.actualizado_en
ORDER BY p.nombre, a.nombre;
