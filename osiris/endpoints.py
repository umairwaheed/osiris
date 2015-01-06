from pyramid.view import view_config
from pyramid.httpexceptions import HTTPOk, HTTPUnauthorized

from osiris.appconst import ACCESS_TOKEN_LENGTH
from osiris.errorhandling import OAuth2ErrorHandler
from osiris.authorization import password_authorization
from osiris.authorization import client_credential_authorization
from osiris.authorization import enable_oauth


@view_config(name='token',
             renderer='json',
             request_method='POST',
             http_cache=0)
def token_endpoint(request):
    """
    The token endpoint is used by the client to obtain an access token by
    presenting its authorization grant or refresh token. The token
    endpoint is used with every authorization grant except for the
    implicit grant type (since an access token is issued directly).
    """

    expires_in = request.registry.settings.get('osiris.tokenexpiry', 0)

    grant_type = request.params.get('grant_type')

    # Authorization Code Grant
    if grant_type == 'authorization_code':
        return OAuth2ErrorHandler.error_unsupported_grant_type()
    # Implicit Grant
    elif grant_type == 'implicit':
        return OAuth2ErrorHandler.error_unsupported_grant_type()
    # Client Credentials
    elif grant_type == 'client_credentials':
        scope = request.params.get('scope', None)  # Optional
        client_id = request.params.get('client_id', None)
        client_secret = request.params.get('client_secret', None)
        if client_id is None:
            return OAuth2ErrorHandler.error_invalid_request(
                    'Required parameter client_id not found in the request')
        elif client_secret is None:
            return OAuth2ErrorHandler.error_invalid_request(
                    'Required parameter client_secret not found in the request'
                    )
        else:
            return client_credential_authorization(request, client_id,
                                                   client_secret, scope,
                                                   expires_in)
    # Client Credentials Grant
    elif grant_type == 'password':
        scope = request.params.get('scope', None)  # Optional
        username = request.params.get('username', None)
        password = request.params.get('password', None)
        if username is None:
            return OAuth2ErrorHandler.error_invalid_request(
                    'Required parameter username not found in the request')
        elif password is None:
            return OAuth2ErrorHandler.error_invalid_request(
                    'Required parameter password not found in the request')
        else:
            return password_authorization(request, username, password, scope,
                                          expires_in)
    else:
        return OAuth2ErrorHandler.error_unsupported_grant_type()


@view_config(name='checktoken',
             renderer='json',
             request_method='POST',
             http_cache=0)
def check_token_endpoint(request):
    """
    This endpoint is out of the oAuth 2.0 specification, however it's needed in
    order to support total desacoplation of the oAuth server and the resource
    servers. When an application (a.k.a. client) impersons the user in order to
    access to the user's resources, the resource server needs to check if the
    token provided is valid and check if it was issued to the user.
    """

    access_token = request.params.get('access_token')
    username = request.params.get('username')
    scope = request.params.get('scope', None)

    if username is None:
        return OAuth2ErrorHandler.error_invalid_request('Required parameter username not found in the request')
    elif access_token is None:
        return OAuth2ErrorHandler.error_invalid_request('Required parameter access_token not found in the request')
    elif len(access_token) != ACCESS_TOKEN_LENGTH:
        return OAuth2ErrorHandler.error_invalid_request('Required parameter not valid found in the request')

    storage = request.registry.osiris_store
    token_info = storage.retrieve(token=access_token)
    if token_info:
        if token_info.get('scope') == scope and token_info.get('username') == username:
            return HTTPOk()
        else:
            return HTTPUnauthorized()

    return HTTPUnauthorized()



@view_config(name='checkoauth',
             renderer='json',
             request_method='POST',
             http_cache=0)
@enable_oauth
def check_oauth_endpoint(request):
    return "Hello World"
