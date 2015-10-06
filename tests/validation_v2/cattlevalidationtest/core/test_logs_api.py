from common_fixtures import *  # NOQA
import websocket as ws
import pytest


def get_logs(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    in_log = random_str()
    cmd = '/bin/bash -c "echo {}; sleep 2"'.format(in_log)
    c = client.create_container(imageUuid=TEST_IMAGE_UUID, command=cmd)
    c = client.wait_success(c)
    logs = c.logs()
    return logs, in_log, c


def test_logs_token(client):
    logs, in_log, c = get_logs(client)
    conn = ws.create_connection(logs.url + '?token='+logs.token)
    result = conn.recv()
    assert result is not None
    assert in_log in result

    delete_all(client, [c])


def test_logs_no_token(client):
    logs, _, c = get_logs(client)
    with pytest.raises(Exception) as excinfo:
            ws.create_connection(logs.url)
    assert 'Handshake status 401' in str(excinfo.value)
    delete_all(client, [c])


def test_host_api_garbage_token(client):
    logs, _, c = get_logs(client)
    with pytest.raises(Exception) as excinfo:
        ws.create_connection(logs.url+'?token=random.garbage.token')
    assert 'Handshake status 401' in str(excinfo.value)
    delete_all(client, [c])
