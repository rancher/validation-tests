from common_fixtures import *  # NOQA
from threading import Thread
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
result = {}

if_lb_drain_testing = pytest.mark.skipif(
    os.environ.get('LB_DRAIN_TESTING') != "true",
    reason='LB Drain testing not enabled')


def create_environment_with_balancer_services(client,
                                              service_scale, lb_scale, port,
                                              internal=False,
                                              lbcookie_policy=None,
                                              config=None,
                                              launch_config_target=None,
                                              target_port=None):

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port, internal,
        lbcookie_policy, config,
        launch_config_target=launch_config_target,
        target_port=target_port)

    service.activate()
    lb_service.activate()

    service = client.wait_success(service, 180)
    lb_service = client.wait_success(lb_service, 180)

    assert service.state == "active"
    assert lb_service.state == "active"
    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    return env, service, lb_service


@if_lb_drain_testing
def test_lb_service_ha_drain_1_scale1(
        client, socat_containers):
    validate_lb_service_ha_drain(client, "9001", service_scale=1,
                                 batch_size=1, startFirst=True)


@if_lb_drain_testing
def test_lb_service_ha_drain_2(
        client, socat_containers):
    validate_lb_service_ha_drain(client, "9002", service_scale=4,
                                 batch_size=2, startFirst=True)


@if_lb_drain_testing
def test_lb_service_ha_drain_3(
        client, socat_containers):
    validate_lb_service_ha_drain(client, "9003", service_scale=4,
                                 batch_size=2, startFirst=False)


@if_lb_drain_testing
def test_lb_service_ha_drain_multiple_clients_startFirst_scale1(
        client, socat_containers):
    validate_lb_service_ha_drain(client, "9004", service_scale=1,
                                 batch_size=1, startFirst=True,
                                 client_thread_count=10)


@if_lb_drain_testing
def test_lb_service_ha_drain_multiple_clients_startFirst(
        client, socat_containers):
    validate_lb_service_ha_drain(client, "9005", service_scale=4,
                                 batch_size=2, startFirst=True,
                                 client_thread_count=10)


@if_lb_drain_testing
def test_lb_service_ha_drain_multiple_clients_no_start_first(
        client, socat_containers):
    validate_lb_service_ha_drain(client, "9006", service_scale=1,
                                 upgrade_start_interval=5,
                                 batch_size=1, startFirst=False,
                                 client_thread_count=5,
                                 per_client_request_count=1)


@if_lb_drain_testing
def test_drain_target_with_multiple_lbs(client, socat_containers):
    lb_services = []
    lb_scale = 1
    service_scale = 2
    lb_port = "9007"
    response_sleep_time = 10000
    draintime_in_ms = 20000
    launch_config_target = {"imageUuid": "docker:prachidamle/testservice",
                            "environment":
                                {"SLEEP_INTERVAL": response_sleep_time},
                            "drainTimeoutMs": draintime_in_ms}
    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, lb_port,
        launch_config_target=launch_config_target,
        target_port=8094)

    lb_services.append(lb_service)

    launch_config_lb = {"imageUuid": get_haproxy_image(),
                        "ports": [lb_port]}

    # Create another LB Service pointing to same target
    random_name = random_str()
    lb_service_name = "LB-" + random_name.replace("-", "")

    port_rule = {"serviceId": service.id,
                 "sourcePort": lb_port,
                 "targetPort": "8094",
                 "protocol": "http"
                 }
    lb_config = {"portRules": [port_rule]}

    lb_service = client.create_loadBalancerService(
        name=lb_service_name,
        stackId=env.id,
        launchConfig=launch_config_lb,
        scale=lb_scale,
        lbConfig=lb_config)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"
    lb_service = client.wait_success(lb_service.activate())
    assert lb_service.state == "active"
    lb_services.append(lb_service)

    upgrade_target_service_when_connecting(
        client, service, lb_services,
        upgrade_start_interval=5,
        batch_size=1, startFirst=True,
        client_thread_count=3,
        per_client_request_count=3)


def validate_lb_service_ha_drain(client, port, service_scale,
                                 upgrade_start_interval=5,
                                 batch_size=1, startFirst=False,
                                 client_thread_count=1,
                                 per_client_request_count=5,
                                 response_sleep_time=20000,
                                 draintime_in_ms=25000):
    launch_config_target = {"imageUuid": "docker:prachidamle/testservice",
                            "environment":
                                {"SLEEP_INTERVAL": response_sleep_time},
                                "drainTimeoutMs": draintime_in_ms}
    lb_scale = 1
    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port,
        launch_config_target=launch_config_target,
        target_port=8094)

    upgrade_target_service_when_connecting(
        client, service, [lb_service],
        upgrade_start_interval=upgrade_start_interval,
        batch_size=batch_size, startFirst=startFirst,
        client_thread_count=client_thread_count,
        per_client_request_count=per_client_request_count)


def upgrade_target_service_when_connecting(
        client, service, lb_services,
        upgrade_start_interval=5,
        batch_size=1, startFirst=False,
        client_thread_count=1,
        per_client_request_count=5):

    client_threads = []

    upgrade_thread = Thread(target=upgrade_service,
                            args=(client, service,
                                  upgrade_start_interval, batch_size,
                                  startFirst))
    upgrade_thread.start()

    for lb_service in lb_services:
        kwargs = {"client": client, "lb_service": lb_service,
                  "service": service, "path": "/connect", "thread_name": "t1",
                  "per_client_request_count": per_client_request_count}
        for i in range(0, client_thread_count):
            thread_name = lb_service.name + "-" + str(i)
            result[thread_name] = False
            kwargs["thread_name"] = thread_name
            client_thread = Thread(target=validate_lb_service, kwargs=kwargs)
            client_threads.append(client_thread)
            client_thread.start()
            time.sleep(.5)

    for i in range(0, client_thread_count*len(lb_services)):
        client_threads[i].join()
    upgrade_thread.join()
    for lb_service in lb_services:
        for i in range(0, client_thread_count):
            res = result[lb_service.name + "-" + str(i)]
            logger.info(
                "Thread " + lb_service.name + str(i) + " : " + str(res))
            assert res


def validate_lb_service(client, lb_service, service, path="/connect",
                        thread_name="t1", per_client_request_count=5):
    lb_containers = get_service_container_list(client, lb_service)
    for lb_con in lb_containers:
        host = lb_con.hosts[0]
    port_string = lb_service.launchConfig.ports[0]
    port = port_string[:port_string.find(":")]
    for i in range(per_client_request_count):
        con_list_pre = get_running_container_names_in_service(client, service)
        response = get_http_response(host, port, path)
        logger.info("Thread:" + thread_name +
                    " Actual responses: " + response)
        con_list1_post = \
            get_running_container_names_in_service(client, service)
        con_list = con_list_pre + con_list1_post
        logger.info("Thread:" + thread_name +
                    " Expected target responses: " + str(con_list))
        if response in con_list:
            result[thread_name] = True
        else:
            result[thread_name] = False
            break


def upgrade_service(
        client, service,
        interval=5, batch_size=1, startFirst=False):
    time.sleep(interval)
    inServiceStrategy = {}
    launch_config_target = service.launchConfig
    launch_config_target["labels"] = {'foo': "bar"}
    inServiceStrategy["launchConfig"] = launch_config_target
    inServiceStrategy["batchSize"] = batch_size,
    inServiceStrategy["intervalMillis"] = 100,
    inServiceStrategy["startFirst"] = startFirst
    service = service.upgrade_action(inServiceStrategy=inServiceStrategy)
    service = client.wait_success(service, 180)
    service.state == "upgraded"
    service = service.finishupgrade()
    service = client.wait_success(service, 180)
    service.state == "active"
