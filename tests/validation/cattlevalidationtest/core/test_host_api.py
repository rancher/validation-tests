from common_fixtures import *  # NOQA
import websocket as ws
import pytest


def test_host_api_token(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    # valid token and a url to the websocket
    stats = hosts[0].stats()
    conn = ws.create_connection(stats.url + '?token='+stats.token)
    result = conn.recv()
    assert result is not None
    assert result.startswith('{')


def test_host_api_no_token(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    # Pass No token
    stats = hosts[0].stats()
    with pytest.raises(Exception) as excinfo:
            ws.create_connection(stats.url)
    assert 'Handshake status 401' in str(excinfo.value)


def test_host_api_garbage_token(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    # pass garbage token
    stats = hosts[0].stats()
    with pytest.raises(Exception) as excinfo:
        ws.create_connection(stats.url+'?token=abcd')
    assert 'Handshake status 401' in str(excinfo.value)
