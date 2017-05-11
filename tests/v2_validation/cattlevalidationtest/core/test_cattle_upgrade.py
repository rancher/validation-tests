from common_fixtures import *  # NOQA
from test_services_lb_ssl_balancer import validate_lb_services_ssl

UPGRADE_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                              'resources/upgrade')

pre_upgrade_stack_name = os.environ.get('PRE_UPGRADE_STACK_NAME')
post_upgrade_stack_name = os.environ.get('POST_UPGRADE_STACK_NAME')
preportsuffixnum = os.environ.get('PRE_PORT_SUFFIX_NUM')
postportsuffixnum = os.environ.get('POST_PORT_SUFFIX_NUM')
preupgrade_stacklist = []
postupgrade_stacklist = []

dom_list = ["test1.com"]

if_pre_upgrade_testing = pytest.mark.skipif(
    os.environ.get('UPGRADE_TESTING') != "true" or
    pre_upgrade_stack_name is None or
    preportsuffixnum is None,
    reason='All parameters needed for UPGRADE_TESTING is not set')

if_post_upgrade_testing = pytest.mark.skipif(
    os.environ.get('UPGRADE_TESTING') != "true" or
    post_upgrade_stack_name is None or
    postportsuffixnum is None,
    pre_upgrade_stack_name is None or
    preportsuffixnum is None,
    reason='All parameters needed for UPGRADE_TESTING is not set')


def pre_upgrade(client):

    # Create certificate to be used in the yml files
    domain = dom_list[0]
    create_cert(client, domain, "test1certificate")
    # Create two stacks
    pre_upgrade_stack1 = pre_upgrade_stack_name + "-1"
    pre_upgrade_stack2 = pre_upgrade_stack_name + "-2"
    create_stacks(client, pre_upgrade_stack1, pre_upgrade_stack2,
                  str(preportsuffixnum))
    validate_stacks(client, pre_upgrade_stack_name,
                    preportsuffixnum, socat_containers)


def create_stacks(client, stack_name1, stack_name2,
                  portsuffixnum):

    # Create pre-upgrade stack
    print "**** In Create Stacks ****"

    print "PORT SUFFIX NUM"

    print portsuffixnum

    lb_image_setting = get_lb_image_version(client)
    print lb_image_setting

    dc_config_file1 = "dc_first_stack.yml"
    rc_config_file1 = "rc_first_stack.yml"
    dc_config1 = readDataFile(UPGRADE_SUBDIR, dc_config_file1)
    dc_config1 = dc_config1.replace("$portsuffixnum", portsuffixnum)
    dc_config1 = dc_config1.replace("$lbimage", lb_image_setting)

    print dc_config1

    rc_config1 = readDataFile(UPGRADE_SUBDIR, rc_config_file1)
    rc_config1 = rc_config1.replace("$portsuffixnum", portsuffixnum)

    print rc_config1
    create_stack_with_service_from_config(client, stack_name1, dc_config1,
                                          rc_config1)

    dc_config_file2 = "dc_second_stack.yml"
    rc_config_file2 = "rc_second_stack.yml"
    dc_config2 = readDataFile(UPGRADE_SUBDIR, dc_config_file2)
    dc_config2 = dc_config2.replace("$stack", stack_name1)
    dc_config2 = dc_config2.replace("$lbimage", lb_image_setting)
    dc_config2 = dc_config2.replace("$portsuffixnum", portsuffixnum)

    print dc_config2

    rc_config2 = readDataFile(UPGRADE_SUBDIR, rc_config_file2)
    rc_config2 = rc_config2.replace("$stack", stack_name1)
    rc_config2 = rc_config2.replace("$portsuffixnum", portsuffixnum)

    create_stack_with_service_from_config(client, stack_name2, dc_config2,
                                          rc_config2)


def validate_stacks(client, stackname,
                    portsuffixnum, socat_containers):

    stack1 = stackname + "-1"
    stack2 = stackname + "-2"
    print "In validate stacks"

    # Validate the containers/lbs in the stack

    stack, service1 = get_env_service_by_name(client, stack1, "service1")
    assert service1['state'] == "active"
    assert service1.scale == 2

    # Validate LB Service

    stack, lbservice = get_env_service_by_name(client, stack1, "mylb")

    assert lbservice['state'] == "active"
    assert lbservice.scale == 1

    mylbport = "300" + str(portsuffixnum)
    validate_lb_service(client, lbservice,
                        mylbport, [service1])

    # Validate health service and health LB Service

    stack, healthservice = get_env_service_by_name(client, stack1,
                                                   "healthservice")
    assert service1['state'] == "active"
    assert healthservice.scale == 1
    assert healthservice.healthState == "healthy"

    stack, healthlbservice = get_env_service_by_name(client, stack1,
                                                     "healthlb")
    healthlbport = "200" + str(portsuffixnum)
    healthlb_containers = get_service_container_list(client,
                                                     healthlbservice)
    for con in healthlb_containers:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)

    healthlbservice = wait_for_condition(
        client, healthlbservice,
        lambda x: x.healthState == 'healthy',
        lambda x: 'State is: ' + x.healthState)

    assert healthlbservice['state'] == "active"
    assert healthlbservice.scale == 1
    assert healthlbservice.healthState == "healthy"

    validate_lb_service(client, healthlbservice,
                        healthlbport, [healthservice])

    # Validate Global Health LB Service
    stack, globalhealthservice = get_env_service_by_name(client, stack1,
                                                         "globalhealthservice")
    assert globalhealthservice['state'] == "active"
    assert globalhealthservice.healthState == "healthy"
    verify_service_is_global(client, globalhealthservice)

    stack, globalhealthlbservice = get_env_service_by_name(client, stack1,
                                                           "globalhealthlb")
    globallbport = "100" + str(portsuffixnum)
    globalhealthlb_containers = get_service_container_list(
        client, globalhealthlbservice)
    for con in globalhealthlb_containers:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)

    globalhealthlbservice = wait_for_condition(
        client, globalhealthlbservice,
        lambda x: x.healthState == 'healthy',
        lambda x: 'State is: ' + x.healthState)

    assert globalhealthlbservice['state'] == "active"
    assert globalhealthlbservice.healthState == "healthy"
    verify_service_is_global(client,
                             globalhealthlbservice)

    validate_lb_service(client, globalhealthlbservice,
                        globallbport, [globalhealthservice])

    stack, service2 = get_env_service_by_name(client, stack1, "service2")
    assert service2['state'] == "active"
    assert service2.scale == 2

    # Validate SSL LB service

    stack, ssllbservice = get_env_service_by_name(client, stack1, "ssllb")
    assert ssllbservice['state'] == "active"
    assert ssllbservice.scale == 1

    ssl_port = "40" + str(portsuffixnum)
    client_port = ssl_port + "0"
    port = ssl_port
    domain = dom_list[0]
    test_ssl_client_con = create_client_container_for_ssh(client, client_port)
    print "***TEST CLIENT CONTAINER***"
    print test_ssl_client_con["port"]
    print test_ssl_client_con["host"]
    print test_ssl_client_con["container"]
    validate_lb_services_ssl(client, test_ssl_client_con,
                             stack, [service1, service2], ssllbservice,
                             port, ssl_port,
                             domain)

    # Validate DNS Service
    stack, servicewithexposedports = get_env_service_by_name(
        client, stack1, "servicewithexposedports")
    assert servicewithexposedports['state'] == "active"
    assert servicewithexposedports.scale == 1
    exposedport = "400" + str(portsuffixnum)
    validate_dns_service(
        client, servicewithexposedports, [service1, service2],
        exposedport, "myalias")

    # Validate DNS of services within a stack using dig servicename
    validate_dns_service(
        client, servicewithexposedports, [healthservice],
        exposedport, "healthservice")

    # Validate External Service
    stack, extservicetohostname = get_env_service_by_name(
        client, stack1, "extservicetohostname")
    validate_external_service_for_hostname(
        client, servicewithexposedports,
        [extservicetohostname], exposedport)

    # Validate Service with Link
    stack, servicewithlink = get_env_service_by_name(client,
                                                     stack1, "servicewithlink")
    assert servicewithlink['state'] == "active"
    assert servicewithlink.scale == 1
    servicelinkexposedport = "500" + str(portsuffixnum)
    validate_linked_service(client, servicewithlink,
                            [service2], servicelinkexposedport,
                            linkName="mylink")

    # Validate LB pointing to a service in the first stack
    # (Cross stack LB validation)

    stack, newstacklbservice = get_env_service_by_name(client, stack2,
                                                       "newstacklb")
    assert newstacklbservice['state'] == "active"
    assert newstacklbservice.scale == 1

    newstacklbport = "600" + str(portsuffixnum)
    validate_lb_service(client, newstacklbservice,
                        newstacklbport, [service2])

    # Validate Service with Link in Second Stack [The link is
    # pointing to a service in the first Stack]
    stack, newstackservice1 = get_env_service_by_name(client, stack2,
                                                      "newstackservice1")
    assert newstackservice1['state'] == "active"
    assert newstackservice1.scale == 1

    stack, newstackservicewithlink = get_env_service_by_name(
        client, stack2, "newstackservicewithlink")
    assert newstackservicewithlink['state'] == "active"
    assert newstackservicewithlink.scale == 1

    newstacklinkedserviceport = "700" + str(portsuffixnum)
    validate_linked_service(client, newstackservicewithlink,
                            [service1], newstacklinkedserviceport,
                            linkName="mynewstacklink")

    # Validate DNS of services across stack using dig servicename.stackname
    dnsname = "newstackservice1." + stack2
    validate_dns_service(
        client, servicewithexposedports, [newstackservice1],
        exposedport, dnsname)

    delete_all(client, [test_ssl_client_con["container"]])
    return


def post_upgrade(client):

    post_upgrade_stack1 = post_upgrade_stack_name+"-1"
    post_upgrade_stack2 = post_upgrade_stack_name+"-2"
    pre_upgrade_stack1 = pre_upgrade_stack_name + "-1"
    pre_upgrade_stack2 = pre_upgrade_stack_name + "-2"
    print "***Validate Pre Stacks in Post UPGRADE ****"
    validate_stacks(client, pre_upgrade_stack_name,
                    preportsuffixnum, socat_containers)
    print "***Modify Pre Stacks in Post UPGRADE ****"
    modify_preupgradestack_verify(client,
                                  pre_upgrade_stack1, pre_upgrade_stack2)

    print "****Create new Stacks in Post UPGRADE ****"
    create_stacks(client, post_upgrade_stack1,
                  post_upgrade_stack2, postportsuffixnum)

    print "****Validate new Stacks in Post UPGRADE ****"
    validate_stacks(client, post_upgrade_stack_name,
                    postportsuffixnum, socat_containers)


def modify_preupgradestack_verify(client,
                                  pre_upgrade_stack1, pre_upgrade_stack2):

    # Increment service scale
    stack, service1 = get_env_service_by_name(client,
                                              pre_upgrade_stack1, "service1")
    service1 = client.update(service1, name=service1.name, scale=3)
    service1 = client.wait_success(service1, 300)
    assert service1.state == "active"
    assert service1.scale == 3

    # Validate LB Service after service increment
    stack, lbservice = get_env_service_by_name(client,
                                               pre_upgrade_stack1, "mylb")
    mylbport = "300" + str(preportsuffixnum)
    validate_lb_service(client, lbservice,
                        mylbport, [service1])

    # Increment LB scale and validate
    lbservice = client.update(lbservice, name=lbservice.name, scale=2)
    lbservice = client.wait_success(lbservice, 300)
    assert lbservice['state'] == "active"
    lbservice.scale == 2
    validate_lb_service(client, lbservice,
                        mylbport, [service1])

    # Validate DNS Service after incrementing service1
    stack, servicewithexposedports = get_env_service_by_name(
        client, pre_upgrade_stack1,
        "servicewithexposedports")
    exposedport = "400" + str(preportsuffixnum)

    validate_dns_service(
        client, servicewithexposedports, [service1],
        exposedport, "service1")

    # Validate Service with Link in NewStack [The link is
    # pointing to a service in Default Stack]
    stack, newstackservice1 = get_env_service_by_name(
        client, pre_upgrade_stack2, "newstackservice1")
    assert newstackservice1.state == "active"
    stack, newstackservicewithlink = get_env_service_by_name(
        client, pre_upgrade_stack2, "newstackservicewithlink")
    newstacklinkedserviceport = "700" + str(preportsuffixnum)
    validate_linked_service(client, newstackservicewithlink,
                            [service1], newstacklinkedserviceport,
                            linkName="mynewstacklink")

    # Increment scale of service2
    stack, service2 = get_env_service_by_name(client,
                                              pre_upgrade_stack1, "service2")
    service2 = client.update(service2, name=service2.name, scale=3)
    service2 = client.wait_success(service2, 300)
    assert service2.state == "active"
    assert service2.scale == 3

    # Validate DNS service as service1 and service2 are incremented
    validate_dns_service(
        client, servicewithexposedports, [service1, service2],
        exposedport, "myalias")

    # Validate LB Service in the second stack after incrementing the LB
    # and service2 to which it is pointing to

    stack, newstacklbservice = \
        get_env_service_by_name(client, pre_upgrade_stack2,
                                "newstacklb")
    newstacklbservice = client.update(newstacklbservice,
                                      name=newstacklbservice.name, scale=2)
    newstacklbservice = client.wait_success(newstacklbservice, 300)
    assert newstacklbservice['state'] == "active"
    newstacklbservice.scale == 2

    newstacklbport = "600" + str(preportsuffixnum)
    validate_lb_service(client, newstacklbservice,
                        newstacklbport, [service2])

    # Validate linked service in the second stack after
    # service1 has been incremented
    stack, newstackservicewithlink = get_env_service_by_name(
        client, pre_upgrade_stack2, "newstackservicewithlink")

    assert newstackservicewithlink['state'] == "active"
    assert newstackservicewithlink.scale == 1

    newstacklinkedserviceport = "700" + str(preportsuffixnum)
    validate_linked_service(client, newstackservicewithlink,
                            [service1], newstacklinkedserviceport,
                            linkName="mynewstacklink")


@if_pre_upgrade_testing
def test_pre_upgrade():
    client = \
        get_client_for_auth_enabled_setup(ACCESS_KEY, SECRET_KEY, PROJECT_ID)
    create_socat_containers(client)
    print "***PRE UPGRADE TEST***"
    pre_upgrade(client)


@if_post_upgrade_testing
def test_post_upgrade():
    client = \
        get_client_for_auth_enabled_setup(ACCESS_KEY, SECRET_KEY, PROJECT_ID)
    client = client
    print "***POST UPGRADE TEST***"
    create_socat_containers(client)
    post_upgrade(client)


def get_lb_image_version(client):

    setting = client.by_id_setting(
        "lb.instance.image")
    default_lb_image_setting = setting.value
    return default_lb_image_setting


def verify_service_is_global(client, service):

    # This method verifies if the service is global

    globalservicetest = client.list_service(name=service.name,
                                            include="instances",
                                            uuid=service.uuid,
                                            state="active")
    print globalservicetest
    print "The length of globalservicetest is:"
    print len(globalservicetest)
    assert len(globalservicetest) == 1
    instanceslist = globalservicetest[0].instances
    print "Instances list"
    print instanceslist
    hostlist = client.list_host(state="active")
    print hostlist
    hostidlist = []
    for host in hostlist:
        hostidlist.append(host.id)

    # Verify that the number of containers of the global service
    # is equal to the number of hosts
    assert len(instanceslist) == len(hostlist)
    print "Host id list"
    print hostidlist
    # Verify that there is one instance per host
    for instance in instanceslist:
        assert instance['hostId'] in hostidlist
        hostidlist.remove(instance['hostId'])
