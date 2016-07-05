from common_fixtures import *  # NOQA


def test_wordpress_template(
        super_client, client, request, catalog_hosts):
    template_name = "wordpress"
    template_version = 0
    env = {"public_port": 80}
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_alfresco_template(
        super_client, client, request, catalog_hosts):
    template_name = "alfresco"
    template_version = 0
    env = {
        "database_name": "alfresco",
        "database_user": "alfresco",
        "database_password": "alfresco"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_zookeeper_template(
        super_client, client, request, catalog_hosts):
    template_name = "zookeeper"
    template_version = 0
    env = {
        "zk_scale": 3,
        "zk_mem": "512",
        "zk_interval": 60
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_asciinema_template(
        super_client, client, request, catalog_hosts):
    template_name = "asciinema-org"
    template_version = 0
    env = {
        "postgres_password": "postgres",
        "host": "localhost",
        "port": 80
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_consul_template(
        super_client, client, request, catalog_hosts):
    template_name = "consul"
    template_version = 0
    ca_cert = "-----BEGIN CERTIFICATE-----\n" \
              "MIIDzzCCAregAwIBAgIJAMvltCWvYD50M" \
              "A0GCSqGSIb3DQEBCwUAMH4xCzAJBgNV\n" \
              "BAYTAlVTMREwDwYDVQQIDAhOZXcgWW9ya" \
              "zEWMBQGA1UEBwwNTmV3IFlvcmsgQ2l0\n" \
              "eTEPMA0GA1UECgwGSE9LU0hBMREwDwYDV" \
              "QQDDAhDb25zdWxDQTEgMB4GCSqGSIb3\n" \
              "DQEJARYRYWRtaW5AZXhhbXBsZS5jb20wH" \
              "hcNMTYwMjE3MTYzNDUxWhcNMjYwMjE0\n" \
              "MTYzNDUxWjB+MQswCQYDVQQGEwJVUzERM" \
              "A8GA1UECAwITmV3IFlvcmsxFjAUBgNV\n" \
              "BAcMDU5ldyBZb3JrIENpdHkxDzANBgNVB" \
              "AoMBkhPS1NIQTERMA8GA1UEAwwIQ29u\n" \
              "c3VsQ0ExIDAeBgkqhkiG9w0BCQEWEWFkb" \
              "WluQGV4YW1wbGUuY29tMIIBIjANBgkq\n" \
              "hkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAp" \
              "9FLEzi8Ty9jhmjA+2kq33bLQzPKNKoT\n" \
              "fx87nzbHmmoOXWjoi9KG3eVgJoF7+sN0y" \
              "aU9pdRx24HP92kOIzjQqVOQNYnzZoYT\n" \
              "uSsnzZ+7oAig931l5FkE1q98Fvw3Cw/RZ" \
              "523tutAgKc3ykNGfdDjaoytX9FwCTYR\n" \
              "NPvF/FNfbk6tvLca3dGz3Gjf8FFDz+aBd" \
              "Ap2nQ6N9hcy9X+ViuNU23uLK0S0HORW\n" \
              "Loh5T2B1wjLkZ91oJCtxP/mrC8H49Ke3R" \
              "pgUOXjjPSAD3wLciuGtH+s4beSgngUD\n" \
              "YihrLQTeT+kGD4XfbgRW3WTHia3tGYBRF" \
              "z0GCk2xQV8N4sQy7Yp0gQIDAQABo1Aw\n" \
              "TjAdBgNVHQ4EFgQUdVoYNrvcp+5/4eUSp" \
              "apT0wI+sxQwHwYDVR0jBBgwFoAUdVoY\n" \
              "Nrvcp+5/4eUSpapT0wI+sxQwDAYDVR0TB" \
              "AUwAwEB/zANBgkqhkiG9w0BAQsFAAOC\n" \
              "AQEAgWpB1X9OHAu7Wcwd+DgqNapHg33jv" \
              "zZgurb2+/wWTVavrUEyyNZS8JYAz2bm\n" \
              "du3r5r6WI1A9VUVQ48WG2cXxJO3bhzk7D" \
              "GQfi5Z1TUNMBEF8HZe2RQdJuJJn0VZ/\n" \
              "8TyTVdrMTjg70sBa/X9NX2lC+s2rxgNqN" \
              "PygiKAijBQ5N5xG/GbvWQRl8nW8Zgx3\n" \
              "jwDzZEDwvgLOLiP331Esg36OPgbavfBea" \
              "k54fIjtwS8ebEOjO7yXRYeuRO8mzUuX\n" \
              "SyLOX10kLrQP6LL1ohhJfdvmToBzO7sBL" \
              "QdgxBHC70ejT+9afVlIjjcDjTVJ8XGh\n" \
              "tLpp/uy/9wOZirqX/43euEBLVQ==\n---" \
              "--END CERTIFICATE-----"
    consul_crt = "-----BEGIN CERTIFICATE-----\n" \
                 "MIIDWTCCAkGgAwIBAgIBCjANBgkqh" \
                 "kiG9w0BAQUFADB+MQswCQYDVQQGEw" \
                 "JVUzER\nMA8GA1UECAwITmV3IFlvc" \
                 "msxFjAUBgNVBAcMDU5ldyBZb3JrIE" \
                 "NpdHkxDzANBgNV\nBAoMBkhPS1NIQ" \
                 "TERMA8GA1UEAwwIQ29uc3VsQ0ExID" \
                 "AeBgkqhkiG9w0BCQEWEWFk\nbWluQ" \
                 "GV4YW1wbGUuY29tMB4XDTE2MDIxNz" \
                 "E2MzcyM1oXDTI2MDIxNDE2MzcyM1o" \
                 "w\nazEWMBQGA1UEAwwNKi5leGFtcG" \
                 "xlLmNvbTERMA8GA1UECAwITmV3IFl" \
                 "vcmsxCzAJ\nBgNVBAYTAlVTMSAwHg" \
                 "YJKoZIhvcNAQkBFhFhZG1pbkBleGF" \
                 "tcGxlLmNvbTEPMA0G\nA1UECgwGSE" \
                 "9LU0hBMIGfMA0GCSqGSIb3DQEBAQU" \
                 "AA4GNADCBiQKBgQDImjP3D9Ob\nIY" \
                 "osJnC/Zw8F+3kQBw6/hIkwE8KSmeT" \
                 "fhQIb4izkC6q4dMjElQ6xUdYXTAXT" \
                 "FshC\nTz/JlbzY9rnVGkC/3jeiDWD" \
                 "42mb+bGmv9glWjnrj1fypPRglOgLC" \
                 "6l3iGX6eDuJB\n5g6PXugWmzpO/Uz" \
                 "ZrREr0fIJUaqjMFwJwQIDAQABo3kw" \
                 "dzAJBgNVHRMEAjAAMB0G\nA1UdDgQ" \
                 "WBBQBYl6Q2Ba9yMoGDm+LDdY3kfhQ" \
                 "pDAfBgNVHSMEGDAWgBR1Whg2u9yn" \
                 "\n7n/h5RKlqlPTAj6zFDALBgNVHQ8EBAMCBaAwH" \
                 "QYDVR0lBBYwFAYIKwYBBQUHAwEG\nCCsGAQUFBw" \
                 "MCMA0GCSqGSIb3DQEBBQUAA4IBAQBfzstljHlDx" \
                 "GZD558ntp0KFE5c\nfsllJBNE9Nx/fRVuF1Yw6m" \
                 "RHoKRS6BGAWawfarNLwTjkcHmjosmFwYRQ+aLEA" \
                 "4Xg\nV0LmyiIApl6F4k7PQPDx94+DzFZBXSz2NX" \
                 "notNKKNVerWC6yIPJ4PxvZuJZIHgVs\nsqqq0KE" \
                 "1oOiAmDF7u93UJnpyrJGMHHmJFQvFEDyCwq7VeD" \
                 "X323fmKLBQPikexhYW\n6dJwVAbcEanCrd8dN7+" \
                 "lW+AZf5N6udn13GoC2Qa6DMqUSdKBti++M7RXtg" \
                 "3tQyv+\nqdveTiEM9K70HuPDIwQIA8zftrHXaSD" \
                 "sq1Lxk3kHu5s7dhYGeBa6OO7Jj5QB\n" \
                 "-----END CERTIFICATE-----"
    consul_key = "-----BEGIN PRIVATE KEY-----\nMIICdwIBAD" \
                 "ANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBA" \
                 "MiaM/cP05shiiwm\ncL9nDwX7eRAHDr+EiTATwp" \
                 "KZ5N+FAhviLOQLqrh0yMSVDrFR1hdMBdMWyEJPP" \
                 "8mV\nvNj2udUaQL/eN6INYPjaZv5saa/2CVaOeu" \
                 "PV/Kk9GCU6AsLqXeIZfp4O4kHmDo9e\n6BabOk7" \
                 "9TNmtESvR8glRqqMwXAnBAgMBAAECgYA1ZC1+jX" \
                 "zRpkyjUZvipahu/C6N\noINBYCIvZKL95+3tu/Y" \
                 "Cu+Ec1SocLCEfiVi+wzxLORW3yDGGzJb6rVr1GD" \
                 "3/TAoW\nHCXN6C+qnmsOWK22fwlBNkpEVen83bz" \
                 "Wh9UAXg2BZ0T/ZF+6+XWvj6pBFi7dzc0H\nDF5F" \
                 "1VpkS5CDR26pAQJBAPbVXkKXcNGNl5frw6QcBrC" \
                 "fZ48zXb7rcoP3lrjRvS9O\nd++CGwIuGY4MtlVQ" \
                 "zLQwyl/Ipr94lSe94hM/tnOoWHECQQDQDVF14R6" \
                 "rEG++eN7D\n9VJRO2Bg/NdZvL1iBvjH98RU/Oau" \
                 "ghYo/3x+zUbXSHcsNSatPL3sGCcSOf/pajj7\nT" \
                 "+5RAkEArHW8HE7vdpq1lmIWGa2zRui5VKaRE3oy" \
                 "Ut5EovF4e3sZ9XA0KrvHAycC\npm2D+Uo1u+LYD" \
                 "uPTYycatFRJyFmRIQJBAM8AUUqN3+uoAOZscIhc" \
                 "L7ju8OfO6Z05\nctxzv1eGp2s/7W03tUC5Ym7vY" \
                 "0qTqS7s+zxmMTkUlttFpd/hdixlzOECQCo7UiQn" \
                 "\nQW4SU3R41XlMB5HoeAVW5KM9bCyx2N2J1vbqA" \
                 "PMsFcI0r5eUWijYzCL4hpgnm0m+\nGkHo5nXWCo" \
                 "At5iM=\n-----END PRIVATE KEY-----"
    gossip_key = "cg8StVXbQJ0gPvMd9o7yrg=="
    env = {
        "ca_crt": ca_cert,
        "consul1_key": consul_key,
        "consul2_key": consul_key,
        "consul3_key": consul_key,
        "consul1_crt": consul_crt,
        "consul2_crt": consul_crt,
        "consul3_crt": consul_crt,
        "gossip_key": gossip_key
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_consul_registrator_template(
        super_client, client, request, catalog_hosts):
    flag = False
    for newproject in super_client.list_project().data:
        if newproject.name == "testcatalog":
            flag = True
            newclient = client_for_project(newproject)
            break
    if not flag:
        newproject = super_client.create_project(name='testcatalog')
        newclient = client_for_project(newproject)
        add_digital_ocean_hosts(newclient, 1)
    hosts = newclient.list_host(kind='docker', removed_null=True)
    testhost = hosts[0]
    ip = testhost.ipAddresses().data[0].address
    c = newclient.create_container(
        name="consulserver",
        ports=[
            '8300:8300',
            '8301:8301',
            '8301:8301/udp',
            '8302:8302',
            '8302:8302/udp',
            '8400:8400',
            '8500:8500',
            '53:53/udp'
              ],
        networkMode=MANAGED_NETWORK,
        imageUuid="docker:progrium/consul:latest",
        requestedHostId=testhost.id,
        command="-advertise " + ip + " -server -bootstrap")
    template_name = "consul-registrator"
    template_version = 0
    env = {
        "consul_server": ip
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    newclient.delete(c)
    remove_catalog_template(client, request, template_name)


def test_etcd_template(
        super_client, client, request, catalog_hosts):
    template_name = "etcd-ha"
    template_version = 0
    env = {
        "REPLICAS": 1
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_fbctf_template(
        super_client, client, request, catalog_hosts):
    template_name = "fbctf"
    template_version = 0
    env = {
        "http_port": "80",
        "https_port": "443",
        "ssl": "true",
        "mysql_database": "fbctf",
        "mysql_user": "fbctf_user",
        "mysql_password": "fbctf_pass"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_ghost_template(
        super_client, client, request, catalog_hosts):
    template_name = "ghost"
    template_version = 0
    env = {
        "public_port": 80
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_gogs_template(
        super_client, client, request, catalog_hosts):
    template_name = "gogs"
    template_version = 0
    env = {
        "http_port": 10080,
        "ssh_port": 222,
        "mysql_password": "password",
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_janitor_template(
        super_client, client, request, catalog_hosts):
    # Version 2
    template_name = "janitor"
    template_version = 2
    env = {
        "FREQUENCY": 3600,
        "EXCLUDE_LABEL": "janitor.exclude=true",
        "KEEP": "rancher/",
        "KEEPC": "*:*"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_jenkins_template(
        super_client, client, request, catalog_hosts):
    template_name = "jenkins-ci"
    template_version = 0
    env = {
        "plugins": "credentials\ngreenballs\ngit\n"
        "junit\ngit-client\ngithub-api\ngithub-oauth\n"
        "github\nplain-credentials\nscm-api\nssh-credentials\n"
        "ssh-slaves\nswarm\n",
        "PORT": 8080
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_jenkins_swarm_template(
        super_client, client, request, catalog_hosts):
    template_name = "jenkins-ci"
    template_version = 0
    env = {
        "plugins": "credentials\ngreenballs\ngit\n"
        "junit\ngit-client\ngithub-api\ngithub-oauth\n"
        "github\nplain-credentials\nscm-api\nssh-credentials\n"
        "ssh-slaves\nswarm\n",
        "PORT": 8080
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    time.sleep(5)
    template_name = "jenkins-swarm"
    template_version = 1
    env = {
        "jenkins_service": "jenkins-ci/jenkins-primary",
        "user": "jenkins"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, "jenkins-swarm")
    remove_catalog_template(client, request, "jenkins-ci")


def test_mongodb_template(
        super_client, client, request, catalog_hosts):
    template_name = "MongoDB"
    template_version = 1
    env = {
        "replset_name": "rs0"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_nuxeo_template(
        super_client, client, request, catalog_hosts):
    template_name = "nuxeo"
    template_version = 0
    env = {
        "packages": "nuxeo-web-mobile nuxeo-drive nuxeo-diff"
        "nuxeo-spreadsheet nuxeo-dam nuxeo-template-rendering"
        "nuxeo-template-rendering-samples nuxeo-showcase-content",
        "volumedriver": "local"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_liferay_template(
        super_client, client, request, catalog_hosts):
    template_name = "liferay"
    template_version = 1
    env = {
        "SETUP_WIZARD_ENABLED": "false",
        "MYSQL_DATABASE": "lportal",
        "MYSQL_USER": "liferay",
        "MYSQL_PASSWORD": "secret",
        "MYSQL_ROOT_PASSWORD": "secret"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_kafka_template(
        super_client, client, request, catalog_hosts):
    template_name = "zookeeper"
    template_version = 0
    env = {
        "zk_scale": 3,
        "zk_mem": "512",
        "zk_interval": 60
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    # Create kafka
    template_name = "kafka"
    template_version = 0
    env = {
        "kafka_scale": 3,
        "kafka_mem": "512",
        "kafka_interval": 60,
        "zk_link": "zookeeper/zk"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, 'zookeeper')
    remove_catalog_template(client, request, 'kafka')


def test_minecraft_template(
        super_client, client, request, catalog_hosts):
    template_name = "minecraft"
    template_version = 0
    env = {
        "EULA": "TRUE",
        "SCALE": 1,
        "PORT": 25565,
        "VERSION": "LATEST",
        "DIFFICULTY": "normal",
        "MODE": "survival",
        "PVP": "false",
        "MOTD": "A Minecraft server powered by Docker"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_galera_template(
        super_client, client, request, catalog_hosts):
    template_name = "galera"
    template_version = 0
    env = {
        "mysql_root_password": "test",
        "mysql_database": "test",
        "mysql_user": "test",
        "mysql_password": "test"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_odoo_template(
        super_client, client, request, catalog_hosts):
    template_name = "odoo"
    template_version = 0
    env = {
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_pxc_template(
        super_client, client, request, catalog_hosts):
    template_name = "pxc"
    template_version = 0
    env = {
        "mysql_root_password": "password",
        "pxc_sst_password": "password"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_prometheus_template(
        super_client, client, request, catalog_hosts):
    template_name = "Prometheus"
    template_version = 1
    env = {
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_puppet_template(
        super_client, client, request, catalog_hosts):
    template_name = "puppet-standalone"
    template_version = 0
    env = {
        "PUPPET_PORT": 8140
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_rabbitmq_template(
        super_client, client, request, catalog_hosts):
    template_name = "rabbitmq-3"
    template_version = 0
    env = {
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_rancher_bench_security_template(
        super_client, client, request, catalog_hosts):
    template_name = "rancher-bench-security"
    template_version = 0
    env = {
        "TRAEFIK_DOMAIN": "ml.innotechapp.com",
        "INTERVAL": 600
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_gocd_agent_template(
        super_client, client, request, catalog_hosts):
    template_name = "gocd-server"
    template_version = 0
    env = {
        "public_port": 8153,
        "mem_initial": 512,
        "mem_max": 1024,
        "volume_work": "/var/lib/docker/go2-server-work",
        "volume_driver": "local"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    template_name = "gocd-agent"
    template_version = 0
    env = {
        "mem_initial": 512,
        "mem_max": 1024,
        "goserver_ip": "gocd-server.rancher.internal",
        "goserver_port": 8153,
        "scale": 1
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, "gocd-server")
    remove_catalog_template(client, request, "gocd-agent")


def test_rocket_chat_template(
        super_client, client, request, catalog_hosts):
    template_name = "rocket-chat"
    template_version = 0
    env = {
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_sysdig_template(
        super_client, client, request, catalog_hosts):
    template_name = "sysdig"
    template_version = 0
    env = {
        "VERSION": "latest",
        "HOST_EXCLUDE_LABEL": "sysdig.exclude_sysdig=true"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_taiga_template(
        super_client, client, request, catalog_hosts):
    template_name = "taiga"
    template_version = 0
    env = {
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_weavescope_template(
        super_client, client, request, catalog_hosts):
    template_name = "weavescope"
    template_version = 1
    env = {
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_wekan_template(
        super_client, client, request, catalog_hosts):
    template_name = "wekan"
    template_version = 0
    env = {
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_xpilot_template(
        super_client, client, request, catalog_hosts):
    template_name = "xpilot"
    template_version = 0
    env = {
        "PASSWORD": "password",
        "DISPLAY": "1.2.3.4",
        "NAME": "player"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


def test_elk_template(
        super_client, client, request, catalog_hosts):
    # Elasticsearch-2
    template_name = "elasticsearch-2"
    template_version = 0
    env = {
        "cluster_name": "es",
        "kopf_port": "80"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    time.sleep(10)
    # Logstash
    template_name = "logstash"
    template_version = 1
    env = {
        "collector_inputs": "udp {\n  port => 5000\n  codec => "
        "\"json\"\n}\ntcp {\n  port => 6000\ncodec => \"json\"\n}\n",
        "indexer_outputs": "elasticsearch {\n  host => \"elasticsearch"
        "\"\n  protocol => \"http\"\n"
        "index => \"logstash-%{+YYYY.MM.dd}\"\n}\n",
        "elasticsearch_link": "elasticsearch-2/elasticsearch-clients"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    time.sleep(10)
    # Kibana
    template_name = "kibana"
    template_version = 1
    env = {
        "elasticsearch_source": "elasticsearch-2/elasticsearch-clients",
        "public_port": 9999
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    # Logspout
    time.sleep(10)
    services = super_client.list_service().data
    for s in services:
        if s.name == "logstash-collector":
            logstash_ip = s.publicEndpoints[0].ipAddress
    template_name = "logspout"
    template_version = 1
    env = {
        "route_uri": "logstash://"+logstash_ip+":53688",
        "public_port": 9999
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, "logspout")
    remove_catalog_template(client, request, "logstash")
    remove_catalog_template(client, request, "kibana")
    remove_catalog_template(client, request, "elasticsearch-2")


def test_gocd_server_template(
        super_client, client, request, catalog_hosts):
    template_name = "gocd-server"
    template_version = 0
    env = {
        "public_port": 8153,
        "mem_initial": 512,
        "mem_max": 1024,
        "volume_work": "/var/lib/docker/go-server-work",
        "volume_driver": "local"
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


# Failed
def test_gitlab_template(
        super_client, client, request, catalog_hosts):
    template_name = "gitlab"
    template_version = 0
    env = {
        "gitlab_hostname": "git.example.com",
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)


# Failed
def test_owncloud_template(
        super_client, client, request, catalog_hosts):
    template_name = "owncloud"
    template_version = 0
    env = {
    }
    deploy_catalog_template(client, super_client, request,
                            template_name, template_version, env)
    remove_catalog_template(client, request, template_name)
