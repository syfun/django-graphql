import asyncio
import json
import traceback
import typing

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import classonlymethod, method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from gql.playground import PLAYGROUND_HTML
from gql.utils import place_files_in_operations
from graphql import ExecutionResult, GraphQLError, GraphQLSchema, graphql, graphql_sync

from .exceptions import GraphQLExtensionError, MethodNotAllowedError, UserInputError
from .response import Response


@method_decorator(csrf_exempt, name='dispatch')
class GraphQLView(View):
    schema: GraphQLSchema = None
    context_value: dict = {}
    enable_playground: bool = True

    http_method_names = ['get', 'post']

    def http_method_not_allowed(self, request, *args, **kwargs):
        raise MethodNotAllowedError()

    def get(self, request, *args, **kwargs):
        if self.enable_playground:
            return HttpResponse(PLAYGROUND_HTML)
        raise MethodNotAllowedError()

    def post(self, request, *args, **kwargs):
        try:
            data = self.parse_body(request)
            return self.get_response(request, data)
        except GraphQLExtensionError as e:
            return Response(data={'errors': [e.formatted]})

    def format_error(self, error: GraphQLError):
        if not error:
            raise ValueError("Received null or undefined error.")
        formatted = dict(  # noqa: E701 (pycqa/flake8#394)
            message=error.message or "An unknown error occurred.",
            locations=[loc._asdict() for loc in error.locations] if error.locations else None,
            path=error.path,
        )
        if settings.DEBUG and error.original_error:
            original_error = error.original_error
            exception = error.extensions.get('exception', {})
            exception['traceback'] = traceback.format_exception(
                type(original_error), original_error, original_error.__traceback__
            )
            error.extensions['exception'] = exception
        if error.extensions:
            formatted.update(extensions=error.extensions)
        return formatted

    def get_response(self, request: HttpRequest, data: dict) -> Response:
        query, variables, operation_name, id = self.get_graphql_params(request, data)

        execution_result = self.execute_graphql_request(request, query, variables, operation_name)

        data = {}
        if not execution_result:
            return Response(data)

        if execution_result.errors:
            data['errors'] = [self.format_error(e) for e in execution_result.errors]
        data['data'] = execution_result.data
        return Response(data)

    def parse_body(self, request: HttpRequest) -> dict:
        content_type = self.get_content_type(request)

        if content_type == 'application/graphql':
            return {'query': request.body.decode()}

        elif content_type == 'application/json':
            try:
                body = request.body.decode()
            except Exception as e:
                raise UserInputError(str(e))

            try:
                return json.loads(body)
            except (TypeError, ValueError):
                raise UserInputError(_('POST body sent invalid JSON.'))

        elif content_type == 'multipart/form-data':
            body = request.POST
            try:
                operations = json.loads(body.get('operations', '{}'))
                files_map = json.loads(body.get('map', '{}'))
            except (TypeError, ValueError):
                raise UserInputError(_('operations or map sent invalid JSON.'))
            if not files_map and not operations:
                return body
            return place_files_in_operations(operations, files_map, request.FILES)

        elif content_type == 'application/x-www-form-urlencoded':
            return request.POST

        return {}

    def execute_graphql_request(self, request, query, variables, operation_name) -> ExecutionResult:
        if not query:
            raise UserInputError(_('Must provide query string.'))
        context = self.context_value or {}
        context['request'] = request
        return graphql_sync(
            self.schema,
            query,
            variable_values=variables,
            context_value=context,
            operation_name=operation_name,
        )

    @staticmethod
    def json_encode(d):
        return json.dumps(d, separators=(',', ':'))

    @staticmethod
    def get_graphql_params(request, data):
        query = request.GET.get('query') or data.get('query')
        variables = request.GET.get('variables') or data.get('variables')
        id = request.GET.get('id') or data.get('id')

        if variables and isinstance(variables, str):
            try:
                variables = json.loads(variables)
            except Exception:
                raise UserInputError(_('Variables are invalid JSON.'))

        operation_name = request.GET.get('operationName') or data.get('operationName')
        if operation_name == 'null':
            operation_name = None

        return query, variables, operation_name, id

    @staticmethod
    def get_content_type(request):
        meta = request.META
        content_type = meta.get('CONTENT_TYPE', meta.get('HTTP_CONTENT_TYPE', ''))
        return content_type.split(';', 1)[0].lower()


class AsyncGraphQLView(GraphQLView):
    @classonlymethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view._is_coroutine = asyncio.coroutines._is_coroutine
        return view

    async def http_method_not_allowed(self, request, *args, **kwargs):
        raise MethodNotAllowedError()

    async def get(self, request, *args, **kwargs):
        if self.enable_playground:
            return HttpResponse(PLAYGROUND_HTML)

        raise MethodNotAllowedError()

    async def post(self, request, *args, **kwargs):
        try:
            data = self.parse_body(request)
            return await self.get_response(request, data)
        except GraphQLExtensionError as e:
            return Response(data={'errors': [e.formatted]})

    async def get_response(self, request: HttpRequest, data: dict) -> Response:
        query, variables, operation_name, id = self.get_graphql_params(request, data)

        execution_result = await self.execute_graphql_request(
            request, query, variables, operation_name
        )

        data = {}
        if not execution_result:
            return Response(data)

        if execution_result.errors:
            data['errors'] = [self.format_error(e) for e in execution_result.errors]
        data['data'] = execution_result.data
        return Response(data)

    async def execute_graphql_request(
        self, request, query, variables, operation_name
    ) -> ExecutionResult:
        if not query:
            raise UserInputError(_('Must provide query string.'))
        context = self.context_value or {}
        context['request'] = request
        return await graphql(
            self.schema,
            query,
            variable_values=variables,
            context_value=context,
            operation_name=operation_name,
        )
