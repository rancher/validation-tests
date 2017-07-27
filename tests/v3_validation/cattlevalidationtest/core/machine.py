from cStringIO import StringIO
import json
import tarfile


def config_from_stream(stream):
    tar = tarfile.open(mode="r:gz", fileobj=StringIO(stream))
    return [json.loads(tar.extractfile(m).read())
            for m in tar.getmembers() if m.name.endswith('/config.json')][0]


def config(client, host):
    return config_from_stream(client._get_response(host.links.config).content)