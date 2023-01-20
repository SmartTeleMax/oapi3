""" Module contains exceptions """


class ApiRequestError(Exception):

    def __init__(self, url, error_text, http_code=None, error_body=None):
        self.url = url
        self.error_text = error_text
        self.http_code = http_code
        self.error_body = error_body
        super().__init__(
            'Request error <url={url}>: {code} {text}'.format(
                url=url,
                code=http_code,
                text=error_text,
            ),
        )


class ValidationError(Exception): pass


class PathNotFound(ValidationError):

    def __init__(self, path):
        self.path = path
        super().__init__('Path={}, error: Path not found'.format(path))


class PathParamValidationError(ValidationError):

    def __init__(self, message):
        super().__init__('Path parameter validation error: {}'.format(message))


class OperationNotAllowed(ValidationError):

    def __init__(self, operation, allowed_operations):
        self.operation = operation
        self.allowed_operations = allowed_operations
        super().__init__(
            'Operation {} not allowed, allowed_operations {}'.format(
                operation,
                ', '.join(allowed_operations),
            )
        )


class OperationError(ValidationError):

    def __init__(self, path, pattern, operation, query, error_message):
        self.path = path
        self.pattern = pattern
        self.operation = operation
        self.query = query
        self.error_message = error_message

        super().__init__(
            'Path={}, pattern={}, operation={}, query={}, error: {}'.format(
                self.path,
                self.pattern,
                self.operation,
                self.query,
                self.error_message,
            ),
        )


class QueryParamValidationError(ValidationError):

    def __init__(self, message):
        super().__init__(
            'Query parameter validation error: {}'.format(message)
        )


class ParameterError(ValidationError):
    pass


class ParameterTypeError(ParameterError):

    def __init__(self, name, value, required_type):
        self.name = name
        self.value = value
        self.required_type = required_type
        super().__init__('Param {}={} must be {} type'.format(
            self.name,
            self.value,
            self.required_type,
        ))


class BodyValidationError(ValidationError):

    def __init__(self, message):
        super().__init__('Body content error: {}'.format(message))


class MediaTypeNotAllowed(BodyValidationError):

    def __init__(self, content_type, allowed_content_types):
        self.content_type = content_type
        super().__init__(
            'Media type {} is not allowed, allowed content types {}'.format(
                content_type,
                ', '.join(allowed_content_types)
            ),
        )


class JsonDecodeError(BodyValidationError):

    def __init__(self, message):
        super().__init__('JSON decode error: {}'.format(message))


class SchemaValidationError(ValidationError):

    def __init__(self, path, message):
        super().__init__(
            'Schema validation error path="{}": {}'.format(
                '.'.join([str(p) for p in path]),
                message,
            ),
        )


class ResponseError(ValidationError):
    pass


class ResponseCodeNotAllowed(ResponseError):

    def __init__(self, response_code, allowed_codes):
        super().__init__(
            'Response code {} is not allowed, allowed codes {}'.format(
                response_code,
                ', '.join(allowed_codes),
            ),
        )
