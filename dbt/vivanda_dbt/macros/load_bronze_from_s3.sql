{% macro load_bronze_from_s3() %}
  {% set tables = [
    'ALMACEN',
    'CATEGORIA',
    'CLIENTE',
    'DETALLE_VENTA',
    'EMPLEADO',
    'INVENTARIO',
    'METODO_PAGO',
    'MOVIMIENTO_INVENTARIO',
    'PAGO',
    'PRODUCTO',
    'PROVEEDOR',
    'SEDE',
    'VENTA'
  ] %}

  {% if execute %}
    {% for table in tables %}
      {% set truncate_sql %}
        TRUNCATE TABLE VIVANDA_DW.BRONZE.{{ table }}
      {% endset %}
      {% do run_query(truncate_sql) %}

      {% set copy_sql %}
        COPY INTO VIVANDA_DW.BRONZE.{{ table }}
        FROM @VIVANDA_DW.BRONZE.VIVANDA_S3_BRONZE/{{ table | lower }}.csv
        FILE_FORMAT = (FORMAT_NAME = 'VIVANDA_DW.BRONZE.VIVANDA_CSV')
        ON_ERROR = 'ABORT_STATEMENT'
        FORCE = TRUE
      {% endset %}
      {% do run_query(copy_sql) %}

      {% do log('Carga Bronze completada: ' ~ table, info=true) %}
    {% endfor %}
  {% endif %}
{% endmacro %}