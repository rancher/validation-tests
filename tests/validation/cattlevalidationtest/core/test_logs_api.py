from common_fixtures import *  # NOQA
import websocket as ws
import pytest
import time


def get_logs(admin_client):
    hosts = admin_client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    inLog = random_str()
    cmd = "/bin/bash -c \"echo "+inLog+"\""
    c = admin_client.create_container(imageUuid=TEST_IMAGE_UUID,
                                      command=cmd)
    c = admin_client.wait_success(c)
    logs = c.logs()
    return logs,inLog,c


def test_logs_token(admin_client):
    logs, inLog,c = get_logs(admin_client)
    conn = ws.create_connection(logs.url + '?token='+logs.token)
    result = conn.recv()
    assert result is not None
    assert inLog in result

    admin_client.delete(c)


def test_logs_no_token(admin_client):
    logs,_ ,c = get_logs(admin_client)
    with pytest.raises(Exception) as excinfo:
            ws.create_connection(logs.url)
    assert 'Handshake status 401' in str(excinfo.value)
    admin_client.delete(c)


def test_host_api_garbage_token(admin_client):
    logs,_ ,c = get_logs(admin_client)
    with pytest.raises(Exception) as excinfo:
        ws.create_connection(logs.url+'?token=random.garbage.token')
    assert 'Handshake status 401' in str(excinfo.value)
    admin_client.delete(c)
