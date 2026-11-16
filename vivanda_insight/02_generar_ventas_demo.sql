-- Demo reversible: hasta 20,000 ventas unitarias de cuatro productos nuevos.
-- La cantidad real queda limitada al stock disponible por encima del mínimo.
-- Productos nuevos: id_producto > 12, activos, sin ventas previas y con stock.
-- Fecha de la demo: octubre de 2026. Ejecutar completo en una sola sesión.

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.pago
        WHERE referencia LIKE 'VIVANDA-EXPO-4PROD-%'
    ) THEN
        RAISE EXCEPTION
            'Ya existe el lote VIVANDA-EXPO-4PROD. Ejecuta primero el script de reversión.';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM public.metodo_pago WHERE activo IS TRUE
    ) THEN
        RAISE EXCEPTION 'No hay un método de pago activo para registrar las ventas.';
    END IF;
END $$;

CREATE TEMP TABLE vivanda_demo_productos ON COMMIT DROP AS
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
ORDER BY p.id_producto
LIMIT 4;

DO $$
DECLARE
    productos_encontrados integer;
BEGIN
    SELECT COUNT(*) INTO productos_encontrados
    FROM vivanda_demo_productos;

    IF productos_encontrados <> 4 THEN
        RAISE EXCEPTION
            'Se encontraron % de 4 productos nuevos elegibles. Revisa el resultado de 01_previsualizar_demo.sql; no se insertó el lote.',
            productos_encontrados;
    END IF;
END $$;

CREATE TEMP TABLE vivanda_demo_lineas ON COMMIT DROP AS
WITH capacidades AS (
    SELECT
        i.id_almacen,
        i.id_producto,
        a.id_sede,
        p.precio,
        FLOOR(GREATEST(i.stock_actual - i.stock_minimo, 0))::bigint
            AS capacidad
    FROM public.inventario AS i
    JOIN vivanda_demo_productos AS p
        ON p.id_producto = i.id_producto
    JOIN public.almacen AS a
        ON a.id_almacen = i.id_almacen
    WHERE a.activo IS TRUE
      AND FLOOR(GREATEST(i.stock_actual - i.stock_minimo, 0)) > 0
      AND EXISTS (
          SELECT 1
          FROM public.empleado AS e
          WHERE e.id_sede = a.id_sede
            AND e.activo IS TRUE
      )
), acumulados AS (
    SELECT
        *,
        SUM(capacidad) OVER (
            ORDER BY id_producto, id_almacen
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) - capacidad AS capacidad_previa
    FROM capacidades
), limite AS (
    SELECT LEAST(20000::bigint, COALESCE(SUM(capacidad), 0)) AS total_ventas
    FROM capacidades
), asignaciones AS (
    SELECT
        a.*,
        LEAST(
            a.capacidad,
            GREATEST(0, l.total_ventas - a.capacidad_previa)
        )::bigint AS ventas_de_esta_ubicacion
    FROM acumulados AS a
    CROSS JOIN limite AS l
), unidades AS (
    SELECT
        a.id_almacen,
        a.id_producto,
        a.id_sede,
        a.precio,
        serie.unidad_numero
    FROM asignaciones AS a
    CROSS JOIN LATERAL generate_series(
        1::bigint,
        a.ventas_de_esta_ubicacion
    ) AS serie(unidad_numero)
), numeradas AS (
    SELECT
        u.*,
        ROW_NUMBER() OVER (
            ORDER BY md5(
                u.id_almacen::text || ':' || u.id_producto::text || ':' ||
                u.unidad_numero::text
            )
        ) AS numero_venta,
        COUNT(*) OVER () AS total_ventas
    FROM unidades AS u
), calendario AS (
    SELECT
        n.*,
        FLOOR((n.numero_venta - 1)::numeric * 21700 / n.total_ventas)::integer
            AS espacio_calendario
    FROM numeradas AS n
)
SELECT
    c.numero_venta,
    NULL::bigint AS id_venta,
    c.id_producto,
    c.id_almacen,
    c.id_sede,
    empleado.id_empleado,
    c.precio AS precio_unitario,
    TIMESTAMPTZ '2026-10-01 09:00:00-05'
        + (c.espacio_calendario / 700) * INTERVAL '1 day'
        + (c.espacio_calendario % 700) * INTERVAL '1 minute'
        AS fecha,
    'VIVANDA-EXPO-4PROD-' || LPAD(c.numero_venta::text, 5, '0')
        AS referencia
FROM calendario AS c
CROSS JOIN LATERAL (
    SELECT e.id_empleado
    FROM public.empleado AS e
    WHERE e.id_sede = c.id_sede
      AND e.activo IS TRUE
    ORDER BY e.id_empleado
    LIMIT 1
) AS empleado;

DO $$
DECLARE
    ventas_preparadas bigint;
BEGIN
    SELECT COUNT(*) INTO ventas_preparadas
    FROM vivanda_demo_lineas;

    IF ventas_preparadas = 0 THEN
        RAISE EXCEPTION 'No hay stock vendible para el lote de demostración.';
    END IF;
END $$;

WITH ventas_insertadas AS (
    INSERT INTO public.venta (
        id_sede, id_empleado, id_cliente,
        fecha, estado, subtotal, descuento, total
    )
    SELECT
        id_sede, id_empleado, NULL,
        fecha, 'COMPLETADA', precio_unitario, 0, precio_unitario
    FROM vivanda_demo_lineas
    ORDER BY numero_venta
    RETURNING id_venta, fecha
)
UPDATE vivanda_demo_lineas AS demo
SET id_venta = venta.id_venta
FROM ventas_insertadas AS venta
WHERE venta.fecha = demo.fecha;

DO $$
DECLARE
    ventas_sin_id bigint;
BEGIN
    SELECT COUNT(*) INTO ventas_sin_id
    FROM vivanda_demo_lineas
    WHERE id_venta IS NULL;

    IF ventas_sin_id > 0 THEN
        RAISE EXCEPTION 'No se pudo asociar el id de venta a todas las líneas.';
    END IF;
END $$;

INSERT INTO public.detalle_venta (
    id_venta, id_producto, cantidad, precio_unitario, descuento
)
SELECT
    id_venta, id_producto, 1, precio_unitario, 0
FROM vivanda_demo_lineas;

INSERT INTO public.pago (
    id_venta, id_metodo_pago, fecha, monto, referencia
)
SELECT
    demo.id_venta,
    metodo.id_metodo_pago,
    demo.fecha,
    demo.precio_unitario,
    demo.referencia
FROM vivanda_demo_lineas AS demo
CROSS JOIN LATERAL (
    SELECT id_metodo_pago
    FROM public.metodo_pago
    WHERE activo IS TRUE
    ORDER BY id_metodo_pago
    LIMIT 1
) AS metodo;

CREATE TEMP TABLE vivanda_demo_salidas ON COMMIT DROP AS
SELECT
    id_almacen,
    id_producto,
    COUNT(*)::numeric AS cantidad
FROM vivanda_demo_lineas
GROUP BY id_almacen, id_producto;

DO $$
DECLARE
    filas_esperadas integer;
    filas_actualizadas integer;
BEGIN
    SELECT COUNT(*) INTO filas_esperadas
    FROM vivanda_demo_salidas;

    UPDATE public.inventario AS i
    SET
        stock_actual = i.stock_actual - salida.cantidad,
        actualizado_en = NOW()
    FROM vivanda_demo_salidas AS salida
    WHERE i.id_almacen = salida.id_almacen
      AND i.id_producto = salida.id_producto
      AND i.stock_actual - salida.cantidad >= i.stock_minimo;

    GET DIAGNOSTICS filas_actualizadas = ROW_COUNT;

    IF filas_actualizadas <> filas_esperadas THEN
        RAISE EXCEPTION
            'El stock cambió durante la operación; se cancela todo el lote. Vuelve a revisar el inventario.';
    END IF;
END $$;

INSERT INTO public.movimiento_inventario (
    id_almacen, id_producto, id_empleado, tipo,
    cantidad, fecha, observacion
)
SELECT
    id_almacen, id_producto, id_empleado, 'SALIDA',
    1, fecha, 'VIVANDA-EXPO-4PROD'
FROM vivanda_demo_lineas;

DO $$
DECLARE
    ventas_generadas bigint;
    detalles_generados bigint;
    pagos_generados bigint;
    movimientos_generados bigint;
BEGIN
    SELECT COUNT(*) INTO ventas_generadas FROM vivanda_demo_lineas;
    SELECT COUNT(*) INTO detalles_generados
    FROM public.detalle_venta AS d
    JOIN vivanda_demo_lineas AS demo ON demo.id_venta = d.id_venta;
    SELECT COUNT(*) INTO pagos_generados
    FROM public.pago
    WHERE referencia LIKE 'VIVANDA-EXPO-4PROD-%';
    SELECT COUNT(*) INTO movimientos_generados
    FROM public.movimiento_inventario
    WHERE observacion = 'VIVANDA-EXPO-4PROD';

    IF ventas_generadas <> detalles_generados
       OR ventas_generadas <> pagos_generados
       OR ventas_generadas <> movimientos_generados THEN
        RAISE EXCEPTION 'La validación del lote no coincide; se cancela la transacción.';
    END IF;
END $$;

SELECT
    p.sku,
    p.nombre AS producto,
    a.nombre AS almacen,
    COUNT(*) AS ventas_generadas,
    SUM(dv.cantidad) AS unidades_vendidas,
    SUM(dv.precio_unitario * dv.cantidad) AS monto_vendido
FROM vivanda_demo_lineas AS demo
JOIN public.producto AS p ON p.id_producto = demo.id_producto
JOIN public.almacen AS a ON a.id_almacen = demo.id_almacen
JOIN public.detalle_venta AS dv ON dv.id_venta = demo.id_venta
GROUP BY p.sku, p.nombre, a.nombre
ORDER BY p.nombre, a.nombre;

SELECT
    COUNT(*) AS total_ventas,
    SUM(precio_unitario) AS total_vendido,
    COUNT(DISTINCT id_producto) AS productos_incluidos
FROM vivanda_demo_lineas;

COMMIT;
