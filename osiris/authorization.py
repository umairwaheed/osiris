from pyramid.interfaces import IAuthenticationPolicy
from pyramid.httpexceptions import HTTPInternalServerError
from osiris.errorhandling import OAuth2ErrorHandler
from osiris.generator import generate_token
from pyramid.settings import asbool


def client_credential_authorization(request, client_id, client_secret, scope,
                                    expires_in):
    client_storage = request.registry.client_store
    client = client_storage.retrieve(client_id=client_id,
                                     client_secret=client_secret)
    identity = client is not None
    return get_token_response(request, client_id, scope, expires_in, identity)


def password_authorization(request, username, password, scope, expires_in):

    ldap_enabled = asbool(request.registry.settings.get('osiris.ldap_enabled'))

    if ldap_enabled:
        from osiris import get_ldap_connector
        connector = get_ldap_connector(request)
        identity = connector.authenticate(username, password)

    else:
        policy = request.registry.queryUtility(IAuthenticationPolicy)
        authapi = policy._getAPI(request)
        credentials = {'login': username, 'password': password}

        identity, headers = authapi.login(credentials)

        return get_token_response(request, username, scope,
                                  expires_in, identity)


def get_token_response(request, username, scope, expires_in, identity):
    if not identity:
        return OAuth2ErrorHandler.error_invalid_grant()
    else:
        storage = request.registry.osiris_store
        # Check if an existing token for the username and scope is already issued
        issued = storage.retrieve(username=username, scope=scope)
        if issued:
            # Return the already issued one
            return dict(access_token=issued.get('token'),
                        token_type='bearer',
                        scope=issued.get('scope'),
                        expires_in=issued.get('expire_time')
                        )
        else:
            # Create and store token
            token = generate_token()
            stored = storage.store(token, username, scope, expires_in)

            # Issue token
            if stored:
                return dict(access_token=token,
                            token_type='bearer',
                            scope=scope,
                            expires_in=int(expires_in)
                            )
            else:
                # If operation error, return a generic server error
                return HTTPInternalServerError()
