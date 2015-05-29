from common_fixtures import *  # NOQA

WEB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/testclient:latest"

logger = logging.getLogger(__name__)


def env_with_2_svc_and_volume_mount_with_config(client, consumed_service_scale,
                                                service_scale,
                                                launch_config_consumed_service,
                                                launch_config_service,
                                                service_is_lb=False):
    # Create Environment
    random_name = random_str()
    env_name = random_name.replace("-", "")
    env = client.create_environment(name=env_name)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create consumed_service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    consumed_service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_consumed_service,
        scale=consumed_service_scale)

    consumed_service = client.wait_success(consumed_service)
    assert consumed_service.state == "inactive"

    # Create service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    if service_is_lb:
        service = client.create_loadBalancerService(
            name=service_name, environmentId=env.id,
            launchConfig=launch_config_service, scale=service_scale,
            dataVolumesFromService=[consumed_service.id])
    else:
        service = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=launch_config_service, scale=service_scale,
            dataVolumesFromService=[consumed_service.id])

    service = client.wait_success(service)
    assert service.state == "inactive"

    return env, consumed_service, service


def create_env_with_2_svc_and_volume_mount(client, consumed_service_scale,
                                           service_scale, label_value,
                                           service_is_lb=False):
    launch_config_consumed_service = {
        "imageUuid": WEB_IMAGE_UUID,
        "labels": {'io.rancher.service.sidekick': label_value}}

    if service_is_lb:
        launch_config_service = {"ports": ["7777:80"],
                                 "labels":
                                 {'io.rancher.service.sidekick': label_value}}
    else:
        launch_config_service = {
            "imageUuid": SSH_IMAGE_UUID,
            "labels": {'io.rancher.service.sidekick': label_value}}
    env, consumed_service, service = \
        env_with_2_svc_and_volume_mount_with_config(
            client, consumed_service_scale, service_scale,
            launch_config_consumed_service, launch_config_service,
            service_is_lb)
    return env, consumed_service, service


def create_env_with_multiple_svcs_and_volume_mounts(
        client, service_scale, label_value):

    launch_config_service = {
        "imageUuid": WEB_IMAGE_UUID,
        "labels": {'io.rancher.service.sidekick': label_value}}

    service_scale_1 = service_scale + 2
    service_scale_2 = service_scale + 1
    service_scale_3 = service_scale - 1
    service_scale_4 = service_scale

    # Create Environment
    random_name = random_str()
    env_name = random_name.replace("-", "")
    env = client.create_environment(name=env_name)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create service4
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service4 = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_service,
        scale=service_scale_4)

    service4 = client.wait_success(service4)
    assert service4.state == "inactive"

    # Create service3 which mounts service4
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service3 = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_service,
        scale=service_scale_3,
        dataVolumesFromService=[service4.id])

    service3 = client.wait_success(service3)
    assert service3.state == "inactive"

    # Create service2 which mounts service3 and service4
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service2 = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_service,
        scale=service_scale_2,
        dataVolumesFromService=[service3.id, service4.id])

    service2 = client.wait_success(service2)
    assert service2.state == "inactive"

    # Create service1 which mounts service2 and service3
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_service,
        scale=service_scale_1,
        dataVolumesFromService=[service2.id, service3.id, service4.id])

    service1 = client.wait_success(service1)
    assert service1.state == "inactive"

    return env, service1, service2, service3, service4


def env_with_2_svc_and_volume_mount(super_client, client,
                                    consumed_service_scale,
                                    service_scale, label_value):

    env, consumed_service, service = create_env_with_2_svc_and_volume_mount(
        client, consumed_service_scale, service_scale, label_value)

    env = env.activateservices()
    env = client.wait_success(env, 300)
    assert env.state == "active"

    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"

    service = client.wait_success(service, 300)
    assert service.state == "active"

    validate_volume_mount(super_client, service, [consumed_service])
    return env, consumed_service, service


def test_volume_mount_lb_services(super_client, client, socat_containers):

    consumed_service_scale = 1
    service_scale = 1

    env, consumed_service, service = create_env_with_2_svc_and_volume_mount(
        client, consumed_service_scale, service_scale, "test1", True)

    env = env.activateservices()
    env = client.wait_success(env, 300)
    assert env.state == "active"

    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"

    service = client.wait_success(service, 300)
    assert service.state == "active"

    validate_volume_mount(super_client, service, [consumed_service])
    delete_all(client, [env])


def test_volume_mount_lb_services_with_different_scale(super_client, client,
                                                       socat_containers):

    consumed_service_scale = 2
    service_scale = 1

    env, consumed_service, service = create_env_with_2_svc_and_volume_mount(
        client, consumed_service_scale, service_scale, "test1", True)

    env = env.activateservices()
    env = client.wait_success(env, 300)
    assert env.state == "active"

    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"

    service = client.wait_success(service, 300)
    assert service.state == "active"

    validate_volume_mount(super_client, service, [consumed_service])
    delete_all(client, [env])


def test_volume_mount_activate_env(super_client, client, socat_containers):

    consumed_service_scale = 2
    service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, consumed_service_scale, service_scale, "test1")

    delete_all(client, [env])


def test_volume_mount_activate_env_with_different_scales(super_client, client,
                                                         socat_containers):

    consumed_service_scale = 1
    service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, consumed_service_scale, service_scale, "test1")

    delete_all(client, [env])


def test_volume_mount_activate_consumed_service(super_client, client,
                                                socat_containers):

    consumed_service_scale = 2
    service_scale = 2

    env, consumed_service, service = create_env_with_2_svc_and_volume_mount(
        client, consumed_service_scale, service_scale, "test1")

    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_activate_service(super_client, client,
                                       socat_containers):

    consumed_service_scale = 2
    service_scale = 2

    env, consumed_service, service = create_env_with_2_svc_and_volume_mount(
        client, consumed_service_scale, service_scale, "test1")

    consumed_service = consumed_service.activate()
    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"

    service = client.wait_success(service, 300)
    assert service.state == "active"

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_multiple_volume_mount_activate_env(super_client, client,
                                            socat_containers):

    service_scale = 2

    env, service1, service2, service3, service4 =\
        create_env_with_multiple_svcs_and_volume_mounts(
            client, service_scale, "test_multiple")

    env = env.activateservices()

    service1 = client.wait_success(service1, 300)
    assert service1.state == "active"
    assert service1.scale == service_scale

    service2 = client.wait_success(service2, 300)
    assert service2.state == "active"
    assert service2.scale == service_scale

    service3 = client.wait_success(service3, 300)
    assert service3.state == "active"
    assert service3.scale == service_scale

    service4 = client.wait_success(service4, 300)
    assert service4.state == "active"
    assert service4.scale == service_scale

    validate_volume_mount(super_client, service1, [service2, service3,
                                                   service4])
    validate_volume_mount(super_client, service2, [service3, service4])
    validate_volume_mount(super_client, service3, [service4])

    delete_all(client, [env])


def test_multiple_volume_mount_activate_service1(super_client, client,
                                                 socat_containers):

    service_scale = 3

    env, service1, service2, service3, service4 =\
        create_env_with_multiple_svcs_and_volume_mounts(
            client, service_scale, "test_multiple")

    service1 = service1.activate()

    service1 = client.wait_success(service1, 300)
    assert service1.state == "active"
    assert service1.scale == service_scale

    service2 = client.wait_success(service2, 300)
    assert service2.state == "active"
    assert service2.scale == service_scale

    service3 = client.wait_success(service3, 300)
    assert service3.state == "active"
    assert service3.scale == service_scale

    service4 = client.wait_success(service4, 300)
    assert service4.state == "active"
    assert service4.scale == service_scale

    validate_volume_mount(super_client, service1, [service2, service3,
                                                   service4])
    validate_volume_mount(super_client, service2, [service3, service4])
    validate_volume_mount(super_client, service3, [service4])

    delete_all(client, [env])


def test_multiple_volume_mount_activate_service2(super_client, client,
                                                 socat_containers):

    service_scale = 4

    env, service1, service2, service3, service4 =\
        create_env_with_multiple_svcs_and_volume_mounts(
            client, service_scale, "test_multiple")

    service2 = service2.activate()
    service2 = client.wait_success(service2, 300)
    assert service2.state == "active"
    assert service2.scale == service_scale

    service1 = client.wait_success(service1, 300)
    assert service1.state == "active"
    assert service1.scale == service_scale

    service3 = client.wait_success(service3, 300)
    assert service3.state == "active"
    assert service3.scale == service_scale

    service4 = client.wait_success(service4, 300)
    assert service4.state == "active"
    assert service4.scale == service_scale

    validate_volume_mount(super_client, service1,
                          [service2, service3, service4])
    validate_volume_mount(super_client, service2, [service3, service4])
    validate_volume_mount(super_client, service3, [service4])

    delete_all(client, [env])


def test_multiple_volume_mount_activate_service3(super_client, client,
                                                 socat_containers):

    service_scale = 2

    env, service1, service2, service3, service4 =\
        create_env_with_multiple_svcs_and_volume_mounts(
            client, service_scale, "test_multiple")

    service3 = service3.activate()

    service3 = client.wait_success(service3, 300)
    assert service3.state == "active"
    assert service3.scale == service_scale

    service1 = client.wait_success(service1, 300)
    assert service1.state == "active"
    assert service1.scale == service_scale

    service2 = client.wait_success(service2, 300)
    assert service2.state == "active"
    assert service2.scale == service_scale

    service4 = client.wait_success(service4, 300)
    assert service4.state == "active"
    assert service4.scale == service_scale

    validate_volume_mount(super_client, service1, [service2, service3,
                                                   service4])
    validate_volume_mount(super_client, service2, [service3, service4])
    validate_volume_mount(super_client, service3, [service4])

    delete_all(client, [env])


def test_multiple_volume_mount_activate_service4(super_client, client,
                                                 socat_containers):

    service_scale = 3

    env, service1, service2, service3, service4 =\
        create_env_with_multiple_svcs_and_volume_mounts(
            client, service_scale, "test_multiple")

    service4 = service4.activate()

    service4 = client.wait_success(service4, 300)
    assert service4.state == "active"
    assert service4.scale == service_scale

    service1 = client.wait_success(service1, 300)
    assert service1.state == "active"
    assert service1.scale == service_scale

    service2 = client.wait_success(service2, 300)
    assert service2.state == "active"
    assert service2.scale == service_scale

    service3 = client.wait_success(service3, 300)
    assert service3.state == "active"
    assert service3.scale == service_scale

    validate_volume_mount(super_client, service1, [service2, service3,
                                                   service4])
    validate_volume_mount(super_client, service2, [service3, service4])
    validate_volume_mount(super_client, service3, [service4])

    delete_all(client, [env])


def test_volume_mount_service_scale_up(super_client, client, socat_containers):

    consumed_service_scale = 2
    service_scale = 2

    final_service_scale = 3

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, consumed_service_scale, service_scale, "test1")

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_service_scale

    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_service_scale

    validate_volume_mount(super_client, service, [consumed_service])
    delete_all(client, [env])


def test_volume_mount_service_scale_down(super_client, client,
                                         socat_containers):
    consumed_service_scale = 4
    service_scale = 4

    final_service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, consumed_service_scale, service_scale, "test1")

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_service_scale

    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_service_scale

    validate_volume_mount(super_client, service, [consumed_service])
    delete_all(client, [env])


def test_volume_mount_consumed_service_scale_up(super_client, client,
                                                socat_containers):

    consumed_service_scale = 2
    service_scale = 2

    final_consumed_service_scale = 3

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, consumed_service_scale, service_scale, "test1")

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_consumed_service_scale

    validate_volume_mount(super_client, service, [consumed_service])
    delete_all(client, [env])


def test_volume_mount_consumed_service_scale_down(super_client, client,
                                                  socat_containers):
    consumed_service_scale = 4
    service_scale = 4

    final_consumed_service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, consumed_service_scale, service_scale, "test1")

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_consumed_service_scale

    validate_volume_mount(super_client, service, [consumed_service])
    delete_all(client, [env])


def test_volume_mount_consumed_services_stop_start_instance(
        super_client, client, socat_containers):

    service_scale = 2
    consumed_service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    container_name = env.name + "_" + consumed_service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    container = client.wait_success(container.stop(), 300)
    assert container.state == 'stopped'

    validate_volume_mount(super_client, service, [consumed_service])

    # Start instance
    container = client.wait_success(container.start(), 300)
    assert container.state == 'running'

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_consumed_services_restart_instance(
        super_client, client, socat_containers):
    service_scale = 2
    consumed_service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    container_name = env.name + "_" + consumed_service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # restart instance
    container = client.wait_success(container.restart(), 300)
    assert container.state == 'running'

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_consumed_services_delete_instance_scale_up(
        super_client, client, socat_containers):

    service_scale = 1
    consumed_service_scale = 3

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    container_name = env.name + "_" + consumed_service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    final_consumed_service_scale = 4

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, consumed_service_scale, service_scale, "test1")

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_consumed_service_scale

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_consumed_services_purge_instance_scale_up(
        super_client, client, socat_containers):

    service_scale = 1
    consumed_service_scale = 3

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    container_name = env.name + "_" + consumed_service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    # purge instance
    container = client.wait_success(container.purge(), 300)

    final_consumed_service_scale = 4

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, consumed_service_scale, service_scale, "test1")

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_consumed_service_scale

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_consumed_services_delete_restore_instance(
        super_client, client, socat_containers):

    service_scale = 1
    consumed_service_scale = 3

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    container_name = env.name + "_" + consumed_service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    # restore instance and start instance
    container = client.wait_success(container.restore(), 300)
    container = client.wait_success(container.start(), 300)

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_consumed_services_deactivate_activate(
        super_client, client, socat_containers):

    service_scale = 1
    consumed_service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    consumed_service = consumed_service.deactivate()
    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "inactive"

    time.sleep(60)

    consumed_service = consumed_service.activate()
    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"
    service = client.wait_success(service, 300)
    assert service.state == "active"

    validate_volume_mount(super_client, service, [consumed_service])
    delete_all(client, [env])


def test_volume_mount_deactivate_activate_environment(super_client, client,
                                                      socat_containers):

    service_scale = 1
    consumed_service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    env = env.deactivateservices()
    service = client.wait_success(service, 300)
    assert service.state == "inactive"

    time.sleep(60)

    env = env.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"

    validate_volume_mount(super_client, service, [consumed_service])
    delete_all(client, [env])


def test_volume_mount_services_stop_start_instance(
        super_client, client, socat_containers):

    service_scale = 2
    consumed_service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    container = client.wait_success(container.stop(), 300)
    assert container.state == 'stopped'

    validate_volume_mount(super_client, service, [consumed_service])

    # Start instance
    container = client.wait_success(container.start(), 300)
    assert container.state == 'running'

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_services_restart_instance(super_client, client,
                                                socat_containers):
    service_scale = 3
    consumed_service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # restart instance
    container = client.wait_success(container.restart(), 300)
    assert container.state == 'running'

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_services_delete_instance_scale_up(
        super_client, client, socat_containers):

    service_scale = 2
    consumed_service_scale = 3

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    container_name = env.name + "_" + service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    final_service_scale = 3

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, consumed_service_scale, service_scale, "test1")

    service = client.update(service,
                            scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_service_scale

    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_service_scale

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_services_purge_instance_scale_up(
        super_client, client, socat_containers):

    service_scale = 2
    consumed_service_scale = 3

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    container_name = env.name + "_" + service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    # purge instance
    container = client.wait_success(container.purge(), 300)

    final_service_scale = 3

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, consumed_service_scale, service_scale, "test1")

    service = client.update(service,
                            scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_service_scale

    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_service_scale

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_services_delete_restore_instance(
        super_client, client, socat_containers):

    service_scale = 1
    consumed_service_scale = 3

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    container_name = env.name + "_" + service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    # restore instance and start instance
    container = client.wait_success(container.restore(), 300)
    container = client.wait_success(container.start(), 300)

    validate_volume_mount(super_client, service, [consumed_service])

    delete_all(client, [env])


def test_volume_mount_services_deactivate_activate(
        super_client, client, socat_containers):

    service_scale = 1
    consumed_service_scale = 2

    env, consumed_service, service = env_with_2_svc_and_volume_mount(
        super_client, client, service_scale, consumed_service_scale, "test2")

    service = service.deactivate()
    service = client.wait_success(service, 300)
    assert service.state == "inactive"

    time.sleep(60)

    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    consumed_service = client.wait_success(consumed_service, 300)
    assert consumed_service.state == "active"

    validate_volume_mount(super_client, service, [consumed_service])
    delete_all(client, [env])


def get_service_container_list(super_client, service):

    container = []
    instance_maps = super_client.list_serviceExposeMap(serviceId=service.id,
                                                       state="active")
    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        containers = super_client.list_container(
            externalId=c.externalId,
            include="hosts")
        assert len(containers) == 1
        container.append(containers[0])

    return container


def get_service_container_name_list(super_client, service):

    container = []
    instance_maps = super_client.list_serviceExposeMap(serviceId=service.id,
                                                       state="active")
    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        containers = super_client.list_container(
            externalId=c.externalId,
            include="hosts")
        assert len(containers) == 1
        container.append(containers[0].externalId)

    return container


def validate_volume_mount(super_client, service, consumed_services):
    print "Validating service - " + service.name

    containers = get_service_container_list(super_client, service)
    assert len(containers) == service.scale

    consolidated_container_list = []
    mounted_container_names = []
    volumes_from_list = []

    for consumed_service in consumed_services:
        print "Validating Consumed Services: " + consumed_service.name
        mounted_containers = get_service_container_name_list(
            super_client, consumed_service)
        assert len(mounted_containers) == consumed_service.scale
        for mounted_container in mounted_containers:
            mounted_container_names.append(mounted_container)
        consolidated_container_list.append(mounted_containers)

    print "All container lists" + str(consolidated_container_list)
    print "All containers" + str(mounted_container_names)

    # For every container in the service , make sure that there is 1
    # mounted container volume from each of the consumed service
    for con in containers:
        host = super_client.by_id('host', con.hosts[0].id)
        docker_client = get_docker_client(host)
        inspect = docker_client.inspect_container(con.externalId)
        volumeFrom = inspect["HostConfig"]["VolumesFrom"]
        print con.name + "->" + str(volumeFrom)
        assert volumeFrom is not None
        assert len(volumeFrom) == len(consumed_services)

        container_list = consolidated_container_list[:]
        container_names = mounted_container_names[:]
        # Check that there is exactly only 1 entry from each of the
        # consumed services
        for volume in volumeFrom:
            volumes_from_list.append(volume)
            found = False
            for volume_list in container_list:
                if volume in volume_list:
                    container_list.remove(volume_list)
                    found = True
            if (not found):
                error_string = \
                    str(volume) + " is not in " + str(container_list)
                assert False, error_string
            # Make sure that the container is in the same host by inspecting it
            inspect = docker_client.inspect_container(volume)
            assert inspect is not None

    # Check that the volumes occur only once in consolidated list of
    # containers
    for volume in volumes_from_list:
        found = False
        for container in container_names:
            if (volume == container):
                container_names.remove(container)
                found = True
        if (not found):
            error_string = \
                str(volume) + " is not in " + str(container_names)
            assert False, error_string
