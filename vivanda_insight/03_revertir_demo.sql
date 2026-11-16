-- Revierte únicamente el lote VIVANDA-EXPO-4PROD.
-- Restaura el inventario usando las salidas marcadas y elimina sus movimientos,
-- detalles, pagos y ventas. No reinicia secuencias/identidades.

BEGIN;

CREATE TEMP TABLE vivanda_demo_ventas_revertir ON COMMIT DROP AS
SELECT DISTINCT id_venta
FROM public.pago
WHERE referencia LIKE 'VIVANDA-EXPO-4PROD-%';

DO $$
DECLARE
    ventas_encontradas bigint;
BEGIN
    SELECT COUNT(*) INTO ventas_encontradas
    FROM vivanda_demo_ventas_revertir;

    IF ventas_encontradas = 0 THEN
        RAISE EXCEPTION 'No se encontró el lote VIVANDA-EXPO-4PROD para revertir.';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.movimiento_inventario
        WHERE observacion = 'VIVANDA-EXPO-4PROD'
          AND tipo = 'SALIDA'
    ) THEN
        RAISE EXCEPTION 'No se encontraron las salidas de inventario del lote; no se modificó nada.';
    END IF;
END $$;

CREATE TEMP TABLE vivanda_demo_stock_reponer ON COMMIT DROP AS
SELECT
    id_almacen,
    id_producto,
    SUM(cantidad) AS cantidad
FROM public.movimiento_inventario
WHERE observacion = 'VIVANDA-EXPO-4PROD'
  AND tipo = 'SALIDA'
GROUP BY id_almacen, id_producto;

DO $$
DECLARE
    filas_esperadas integer;
    filas_actualizadas integer;
BEGIN
    SELECT COUNT(*) INTO filas_esperadas
    FROM vivanda_demo_stock_reponer;

    UPDATE public.inventario AS i
    SET
        stock_actual = i.stock_actual + salida.cantidad,
        actualizado_en = NOW()
    FROM vivanda_demo_stock_reponer AS salida
    WHERE i.id_almacen = salida.id_almacen
      AND i.id_producto = salida.id_producto;

    GET DIAGNOSTICS filas_actualizadas = ROW_COUNT;

    IF filas_actualizadas <> filas_esperadas THEN
        RAISE EXCEPTION 'No se pudo restaurar todo el inventario; se cancela la reversión.';
    END IF;
END $$;

DELETE FROM public.detalle_venta AS d
USING vivanda_demo_ventas_revertir AS demo
WHERE d.id_venta = demo.id_venta;

DELETE FROM public.pago
WHERE referencia LIKE 'VIVANDA-EXPO-4PROD-%';

DELETE FROM public.venta AS v
USING vivanda_demo_ventas_revertir AS demo
WHERE v.id_venta = demo.id_venta;

DELETE FROM public.movimiento_inventario
WHERE observacion = 'VIVANDA-EXPO-4PROD';

SELECT
    (SELECT COUNT(*) FROM vivanda_demo_ventas_revertir) AS ventas_revertidas,
    (SELECT COUNT(*) FROM vivanda_demo_stock_reponer) AS ubicaciones_de_stock_restauradas;

COMMIT;
