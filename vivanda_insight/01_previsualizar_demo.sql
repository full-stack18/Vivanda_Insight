-- Previsualiza los primeros cuatro productos nuevos con stock vendible.
-- Se consideran nuevos los productos activos con id_producto > 12
-- que todavía no aparecen en detalle_venta.

WITH productos_disponibles AS (
    SELECT
        p.id_producto,
        p.sku,
        p.nombre AS producto,
        p.precio,
        SUM(FLOOR(GREATEST(i.stock_actual - i.stock_minimo, 0)))::bigint
            AS unidades_vendibles
    FROM public.producto AS p
    JOIN public.inventario AS i
        ON i.id_producto = p.id_producto
    JOIN public.almacen AS a
        ON a.id_almacen = i.id_almacen
    WHERE p.id_producto > 12
      AND p.activo IS TRUE
      AND a.activo IS TRUE
      AND EXISTS (
          SELECT 1
          FROM public.empleado AS e
          WHERE e.id_sede = a.id_sede
            AND e.activo IS TRUE
      )
      AND NOT EXISTS (
          SELECT 1
          FROM public.detalle_venta AS dv
          WHERE dv.id_producto = p.id_producto
      )
    GROUP BY p.id_producto, p.sku, p.nombre, p.precio
    HAVING SUM(FLOOR(GREATEST(i.stock_actual - i.stock_minimo, 0))) > 0
), seleccion AS (
    SELECT *
    FROM productos_disponibles
    ORDER BY id_producto
    LIMIT 4
)
SELECT
    id_producto,
    sku,
    producto,
    precio,
    unidades_vendibles,
    SUM(unidades_vendibles) OVER () AS stock_total_vendible_de_los_4,
    LEAST(20000::bigint, SUM(unidades_vendibles) OVER ())
        AS ventas_que_generara_el_script
FROM seleccion
ORDER BY id_producto;
