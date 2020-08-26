import typing

from django.db.models import Field, FieldDoesNotExist, Model, Prefetch, QuerySet
from gql.parser import FieldMeta


def get_only_cols(model: Model, sections: typing.List[str]) -> typing.List[str]:
    cols = []
    for section in sections:
        try:
            f: Field = model._meta.get_field(section)
            cols.append(f.get_attname())
        except FieldDoesNotExist:
            continue

    return cols


def get_related_cols(
    model: Model, sub_fields: typing.Dict[str, FieldMeta]
) -> typing.Tuple[typing.List[str], typing.List[Prefetch]]:
    return [], []


def optimize_query(query: QuerySet, meta: FieldMeta) -> QuerySet:
    model = query.model
    only_cols = get_only_cols(model, meta.sections)
    select_related_cols, prefetchs = get_related_cols(model, meta.sub_fields)
    if only_cols:
        query = query.only(*only_cols)
    if select_related_cols:
        query = query.select_related(*select_related_cols)
    if prefetchs:
        query = query.prefetch_related(*prefetchs)
    return query
