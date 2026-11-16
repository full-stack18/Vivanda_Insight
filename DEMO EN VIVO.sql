SELECT
    (SELECT COUNT(*)
     FROM public.pago
     WHERE referencia LIKE 'DEMO20K-2026-%') AS pagos_marcados,
    (SELECT COUNT(DISTINCT id_venta)
     FROM public.pago
     WHERE referencia LIKE 'DEMO20K-2026-%') AS ventas_marcadas,
    (SELECT COUNT(*)
     FROM public.detalle_venta d
     WHERE EXISTS (
         SELECT 1
         FROM public.pago p
         WHERE p.id_venta = d.id_venta
           AND p.referencia LIKE 'DEMO20K-2026-%'
     )) AS detalles_marcados;