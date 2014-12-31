"""MongoDB UserStore implementation"""

import datetime
from pymongo import MongoClient
from pymongo import MongoReplicaSetClient
from pymongo.errors import ConnectionFailure
from pymongo.errors import OperationFailure
from pymongo.errors import AutoReconnect

from pyramid.decorator import reify
from pyramid.exceptions import ConfigurationError
from pyramid.settings import asbool

from osiris.store.interface import TokenStore


def includeme(config):
    settings = config.registry.settings
    host = settings.get('osiris.store.host', 'localhost')
    port = int(settings.get('osiris.store.port', '27017'))
    db = settings.get('osiris.store.db', 'osiris')
    collection = settings.get('osiris.store.collection', 'tokens')
    client_collection = settings.get('osiris.store.client_collection',
                                     'clients')
    enable_cluster = asbool(settings.get('osiris.mongodb.cluster', False))
    hosts = settings.get('osiris.mongodb.hosts', 'localhost:27017')
    replica_set = settings.get('osiris.mongodb.replica_set', '')
    use_greenlets = settings.get('osiris.mongodb.use_greenlets', '')

    store = TokenDB(
        host=host, port=port, db=db, collection=collection,
        enable_cluster=enable_cluster, hosts=hosts, replica_set=replica_set,
        use_greenlets=use_greenlets
    )

    client = ClientDB(
        host=host, port=port, db=db, collection=client_collection,
        enable_cluster=enable_cluster, hosts=hosts, replica_set=replica_set,
        use_greenlets=use_greenlets
    )

    config.registry.osiris_store = store
    config.registry.client_store = client


def handle_reconnects(fun):
    def replacement(*args, **kwargs):
        # Handle exceptions in case of database operational error
        try:
            response = fun(*args, **kwargs)
        except AutoReconnect:
            tryin_to_reconnect = True
            while tryin_to_reconnect:
                try:
                    response = fun(*args, **kwargs)
                except AutoReconnect:
                    pass
                else:
                    tryin_to_reconnect = False
        else:
            return response
    return replacement


class MongoDBStore(TokenStore):
    """MongoDB Storage for oAuth tokens"""
    def __init__(self, host='localhost', port=27017, db="osiris",
                 collection='tokens', enable_cluster=False, hosts='',
                 replica_set='', use_greenlets=False):
        self.host = host
        self.port = port
        self.db = db
        self.collection = collection
        self.enable_cluster = enable_cluster
        self.hosts = hosts
        self.replica_set = replica_set
        self.use_greenlets = use_greenlets

    @reify
    def _conn(self):
        """The MongoDB connection, cached for this call"""
        try:
            if not self.enable_cluster:
                db_conn = MongoClient(self.host, self.port, slave_okay=False)
            else:
                db_conn = MongoReplicaSetClient(self.hosts,
                                                replicaSet=self.replica_set,
                                                use_greenlets=self.use_greenlets)
        except ConnectionFailure:
            raise Exception('Unable to connect to MongoDB')
        conn = db_conn[self.db]

        if not self.collection in conn.collection_names():
            conn.create_collection(self.collection)

        return conn

    @handle_reconnects
    def retrieve(self, **kwargs):
        query = dict([(k, v) for k, v in kwargs.items() if v])
        data = self._conn[self.collection].find_one(query)
        if data:
            return data
        else:
            return None

    @handle_reconnects
    def store(self, **kwargs):
        try:
            self._conn[self.collection].insert(kwargs)
        except OperationFailure:
            return False
        else:
            return True

    @handle_reconnects
    def delete(self, **kwargs):
        try:
            self._conn[self.collection].remove(kwargs)
        except OperationFailure:
            return False
        else:
            return True

    def purge_expired(self):
        pass


class TokenDB(MongoDBStore):
    """MongoDB Storage for oAuth tokens"""

    def store(self, token, username, scope, expires_in):
        data = {}
        data['username'] = username
        data['token'] = token
        data['scope'] = scope
        data['issued_at'] = datetime.datetime.utcnow()
        if expires_in == '0':
            data['expire_time'] = 0
        else:
            data['expire_time'] = datetime.datetime.utcnow() + \
                datetime.timedelta(seconds=int(expires_in))

        return super(TokenDB, self).store(**data)

    def delete(self, token):
        return super(TokenDB, self).delete(token=token)


class ClientDB(MongoDBStore):
    """MongoDB Storage for clients"""

    def store(self, client_id, client_secret):
        return super(ClientDB, self).store(client_id=client_id,
                                          client_secret=client_secret)

    def delete(self, client_id):
        return super(ClientDB, self).delete(client_id=client_id)
