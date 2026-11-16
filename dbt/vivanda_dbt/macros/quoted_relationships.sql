{% test quoted_relationships(model, column_name, to, field) %}

select child.{{ adapter.quote(column_name) }} as from_field
from {{ model }} as child
left join {{ to }} as parent
  on child.{{ adapter.quote(column_name) }} =
     parent.{{ adapter.quote(field) }}
where child.{{ adapter.quote(column_name) }} is not null
  and parent.{{ adapter.quote(field) }} is null

{% endtest %}