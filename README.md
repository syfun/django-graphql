# Django Graphql


## How to use
```python
import typing
from enum import Enum

from django.conf import settings
from gql import query, gql, type_resolver, enum_type, field_resolver, make_schema_from_file
from djgql.auth import login_required
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
@login_required
def hero(parent, info, episode: typing.Optional[Episode]) -> typing.Optional[Character]:
    request = info.context['request']
    print(request.user)
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


schema = make_schema_from_file(settings.GRAPHQL_SCHEMA_FILE)
```

```python
# urls.py
from django.contrib import admin
from django.urls import path

from djgql.views import GraphQLView
from .schema import schema

urlpatterns = [
    path('admin/', admin.site.urls),
    path('graphql/', GraphQLView.as_view(schema=schema))
]
```

```python
# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'djgql.auth.middleware.BasicAuthMiddleware',
]
GRAPHQL_SCHEMA_FILE = os.path.join(BASE_DIR, 'starwar.gql')
```


