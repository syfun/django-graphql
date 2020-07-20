# Django Graphql

## gqlgen

gqlgen is a generator tool for GraphQL.

```shell script
Usage: gqlgen [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  all             Generate all schema types
  field-resolver  Generate field resolver.
  type            Generate one type
  type-resolver   Generate all schema types

```


## How to use

```python
# urls.py
from django.contrib import admin
from django.urls import path

from djgql.views import GraphQLView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('graphql/', GraphQLView.as_view())
]
```

```python
# settings.py
GRAPHQL_SCHEMA_FILE = os.path.join(BASE_DIR, 'starwar.gql')
GRAPHQL = {
    'SCHEMA': 'starwar.schema.schema',
    'ENABLE_PLAYGROUND': True
}
```

```python
import typing
from enum import Enum

from django.conf import settings
from gql import query, gql, type_resolver, enum_type, field_resolver
from gql.build_schema import build_schema_from_file
from pydantic import BaseModel

type_defs = gql("""
type Query {
    hello(name: String!): String!
}
""")


@enum_type
class Episode(Enum):
    NEWHOPE = 1
    EMPIRE = 2
    JEDI = 3


class Character(BaseModel):
    id: typing.Text
    name: typing.Optional[typing.Text]
    friends: typing.Optional[typing.List[typing.Optional['Character']]]
    appears_in: typing.Optional[typing.List[typing.Optional[Episode]]]


class Human(Character):
    id: typing.Text
    name: typing.Optional[typing.Text]
    friends: typing.Optional[typing.List[typing.Optional[Character]]]
    appears_in: typing.Optional[typing.List[typing.Optional[Episode]]]
    home_planet: typing.Optional[typing.Text]


class Droid(Character):
    id: typing.Text
    name: typing.Optional[typing.Text]
    friends: typing.Optional[typing.List[typing.Optional[Character]]]
    appears_in: typing.Optional[typing.List[typing.Optional[Episode]]]
    primary_function: typing.Optional[typing.Text]


@query
def hero(parent, info, episode: typing.Optional[Episode]) -> typing.Optional[Character]:
    return Human(id='test')


@field_resolver('Human', 'name')
def human_name(parent, info):
    return 'Jack'


@type_resolver('Character')
def resolve_character_type(obj, info, type_):
    if isinstance(obj, Human):
        return 'Human'
    if isinstance(obj, Droid):
        return 'Droid'
    return None


schema = build_schema_from_file(settings.GRAPHQL_SCHEMA_FILE)
```