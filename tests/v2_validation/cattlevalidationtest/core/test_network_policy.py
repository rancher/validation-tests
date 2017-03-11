from common_fixtures import *  # NOQA
test_network_policy = os.environ.get(
    'TEST_NETWORK_POLICY', "False")

np_reason = \
    'Intended to not execute this network policy test'

if_network_policy = pytest.mark.skipif(test_network_policy != "ALL",
                                       reason=np_reason)
if_network_policy_none = pytest.mark.skipif(
    test_network_policy != "NONE",
    reason=np_reason)
if_network_policy_within_stack = pytest.mark.skipif(
    test_network_policy != "WITHIN_STACK",
    reason=np_reason)
if_network_policy_within_service = pytest.mark.skipif(
    test_network_policy != "WITHIN_SERVICE",
    reason=np_reason)
if_network_policy_within_linked = pytest.mark.skipif(
    test_network_policy != "WITHIN_LINKED",
    reason=np_reason)
if_network_policy_groupby = pytest.mark.skipif(
    test_network_policy != "WITHIN_GROUPBY",
    reason=np_reason)


NETWORKPOLICY_SUBDIR = \
    os.path.join(os.path.dirname(os.path.realpath(__file__)),
                 'resources/networkpolicy')
policy_within_stack = {"within": "stack", "action": "allow"}
policy_groupby = {"between": {"groupBy": "com.rancher.stack.location"},
                  "action": "allow"}
policy_within_service = {"within": "service", "action": "allow"}
policy_within_linked = {"within": "linked", "action": "allow"}
shared_environment = {"env": []}


@pytest.fixture(scope='session', autouse=True)
def create_env_for_network_policy(request, client, socat_containers):
    assert check_for_network_policy_manager(client)
    env2 = create_stack_with_service(client, "test2", NETWORKPOLICY_SUBDIR,
                                     "stack2.yml", "stack2-rc.yml")
    assert len(env2.services()) == 6
    env1 = create_stack_with_service(client, "test1", NETWORKPOLICY_SUBDIR,
                                     "stack1.yml", "stack1-rc.yml")
    assert len(env1.services()) == 11

    create_standalone_containers(client)
    time.sleep(sleep_interval)
    populate_env_details(client)

    def fin():
        to_delete = [env1, env2]
        delete_all(client, to_delete)
        delete_all(client, shared_environment["containers"])
        delete_all(client, shared_environment["containers_with_label"])

    request.addfinalizer(fin)


def populate_env_details(client):
    env = client.list_stack(name="test1")
    assert len(env) == 1
    env1 = env[0]
    env = client.list_stack(name="test2")
    assert len(env) == 1
    env2 = env[0]

    shared_environment["env"].append(env1)
    shared_environment["env"].append(env2)
    shared_environment["stack1_test1allow"] = \
        get_service_by_name(client, env1,  "test1allow")
    shared_environment["stack1_test2allow"] = \
        get_service_by_name(client, env1,  "test2allow")
    shared_environment["stack1_test3deny"] = \
        get_service_by_name(client, env1,  "test3deny")
    shared_environment["stack1_test4deny"] = \
        get_service_by_name(client, env1,  "test4deny")
    shared_environment["stack1_lbwithinstack"] = \
        get_service_by_name(client, env1,  "lbwithininstack")
    shared_environment["stack1_lbcrossstack"] = \
        get_service_by_name(client, env1,  "lbcrossstack")
    shared_environment["stack1_servicewithlinks"] = \
        get_service_by_name(client, env1,  "servicewithlinks")
    shared_environment["stack1_servicecrosslinks"] = \
        get_service_by_name(client, env1,  "servicecrosslinks")
    shared_environment["stack1_servicelinktosidekick"] = \
        get_service_by_name(client, env1,  "servicelinktosidekick")
    shared_environment["stack1_linktowebservice"] = \
        get_service_by_name(client, env1,  "linktowebservice")

    shared_environment["stack2_test1allow"] = \
        get_service_by_name(client, env2,  "test1allow")
    shared_environment["stack2_test2allow"] = \
        get_service_by_name(client, env2,  "test2allow")
    shared_environment["stack2_test3deny"] = \
        get_service_by_name(client, env2,  "test3deny")
    shared_environment["stack2_test4deny"] = \
        get_service_by_name(client, env2,  "test4deny")

    service_with_sidekick = {}
    service_with_sidekick["p_con1"] = \
        get_container_by_name(client, "test2-testp1-1")
    service_with_sidekick["p_con2"] = \
        get_container_by_name(client, "test2-testp1-2")
    service_with_sidekick["s1_con1"] = \
        get_container_by_name(client, "test2-testp1-tests1-1")
    service_with_sidekick["s1_con2"] = \
        get_container_by_name(client, "test2-testp1-tests1-2")
    service_with_sidekick["s2_con1"] = \
        get_container_by_name(client, "test2-testp1-tests2-1")
    service_with_sidekick["s2_con2"] = \
        get_container_by_name(client, "test2-testp1-tests2-2")
    shared_environment["stack2_sidekick"] = service_with_sidekick
    time.sleep(sleep_interval)


def validate_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client):
    # Validate that standalone containers are not able reach any
    # service containers
    for container in shared_environment["containers"]:
        validate_connectivity_between_con_to_services(
            admin_client, container,
            [shared_environment["stack1_test2allow"],
             shared_environment["stack2_test4deny"]],
            connection="deny")
    # Validate that there connectivity between containers of different
    # services within the same stack is allowed
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test1allow"],
        [shared_environment["stack1_test2allow"],
         shared_environment["stack1_test3deny"],
         shared_environment["stack1_test4deny"]],
        connection="allow")
    # Validate that there is no connectivity between containers of different
    # services across stacks
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test1allow"],
        [shared_environment["stack2_test1allow"],
         shared_environment["stack2_test2allow"],
         shared_environment["stack2_test3deny"],
         shared_environment["stack2_test4deny"]],
        connection="deny")
    # Validate that LB is able reach all targets which are in the same stack as
    # Lb
    validate_lb_service(admin_client, admin_client,
                        shared_environment["stack1_lbwithinstack"],
                        "9091",
                        [shared_environment["stack1_test1allow"]])
    # Validate that LB is able reach all targets which are in the same stack as
    # Lb
    validate_linked_service(admin_client,
                            shared_environment["stack1_servicewithlinks"],
                            [shared_environment["stack1_test1allow"]],
                            "99")
    # Cross stacks access for links should be denied
    validate_linked_service(admin_client,
                            shared_environment["stack1_servicecrosslinks"],
                            [shared_environment["stack2_test2allow"]],
                            "98", linkName="test2allow.test2",
                            not_reachable=True)
    # Cross stacks access for LBs should be denied
    validate_lb_service_for_no_access(
        admin_client, shared_environment["stack1_lbcrossstack"], "9090")


def validate_default_network_action_deny_networkpolicy_none(
        admin_client):
    # Validate that standalone containers are not able reach any
    # service containers
    for container in shared_environment["containers"]:
        validate_connectivity_between_con_to_services(
            admin_client, container,
            [shared_environment["stack1_test2allow"],
             shared_environment["stack2_test4deny"]],
            connection="deny")
    # Validate that there is no connectivity between containers of different
    # services across stacks and within stacks
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test1allow"],
        [shared_environment["stack1_test2allow"],
         shared_environment["stack1_test3deny"],
         shared_environment["stack1_test4deny"],
         shared_environment["stack2_test1allow"],
         shared_environment["stack2_test2allow"],
         shared_environment["stack2_test3deny"],
         shared_environment["stack2_test4deny"]],
        connection="deny")
    # Validate that Lb service is not able to reach targets within the
    # same stack and cross stacks
    validate_lb_service_for_no_access(
        admin_client, shared_environment["stack1_lbwithinstack"], "9091")
    validate_lb_service_for_no_access(
        admin_client, shared_environment["stack1_lbcrossstack"], "9090")

    # Validate that connectivity between linked service is denied within the
    # same stack and  cross stacks
    validate_linked_service(admin_client,
                            shared_environment["stack1_servicewithlinks"],
                            [shared_environment["stack1_test1allow"]],
                            "99", not_reachable=True)
    validate_linked_service(admin_client,
                            shared_environment["stack1_servicecrosslinks"],
                            [shared_environment["stack2_test2allow"]],
                            "98", linkName="test2allow.test2",
                            not_reachable=True)


def validate_default_network_action_deny_networkpolicy_groupby(
        admin_client):
    # Validate that containers that do not have the labels defined
    # in group by policy are not allowed to communicate with other
    # service containers
    for container in shared_environment["containers"]:
        validate_connectivity_between_con_to_services(
            admin_client, container,
            [shared_environment["stack1_test2allow"],
             shared_environment["stack2_test4deny"]],
            connection="deny")
    # Validate that stand alone  containers that have the labels defined
    # in group by policy are allowed to communicate with service containers
    # having the same labels
    for container in shared_environment["containers_with_label"]:
        validate_connectivity_between_con_to_services(
            admin_client, container,
            [shared_environment["stack1_test2allow"],
             shared_environment["stack2_test1allow"],
             shared_environment["stack2_test2allow"]],
            connection="allow")

    # Validate that service containers that have matching labels defined
    # in group by policy are allowed to communicate with each other
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test1allow"],
        [shared_environment["stack1_test2allow"],
         shared_environment["stack2_test1allow"],
         shared_environment["stack2_test2allow"]],
        connection="allow")

    # Validate that all service containers within the same service that has
    # group by labels are able to communicate with each other
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test3deny"],
        [shared_environment["stack2_test3deny"]],
        connection="allow")

    # Validate that service containers that do not have matching labels defined
    # in group by policy are not allowed to communicate with each other
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test1allow"],
        [shared_environment["stack1_test3deny"],
         shared_environment["stack1_test4deny"],
         shared_environment["stack2_test3deny"],
         shared_environment["stack2_test4deny"]],
        connection="deny")
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test3deny"],
        [shared_environment["stack1_test1allow"],
         shared_environment["stack1_test2allow"],
         shared_environment["stack1_test4deny"],
         shared_environment["stack2_test1allow"],
         shared_environment["stack2_test2allow"],
         shared_environment["stack2_test4deny"]],
        connection="deny")


def validate_default_network_action_deny_networkpolicy_within_service(
        admin_client):
    # Validate that standalone containers are not able reach any
    # service containers
    for container in shared_environment["containers"]:
        validate_connectivity_between_con_to_services(
            admin_client, container,
            [shared_environment["stack1_test1allow"],
             shared_environment["stack2_test4deny"]],
            connection="deny")

    # Validate that containers belonging to the same service are able to
    # communicate with each other
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test1allow"],
        [shared_environment["stack1_test1allow"]],
        connection="allow")

    # Validate that containers belonging to the different services within
    # the same stack or cross stack are not able to communicate with each other
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test1allow"],
        [shared_environment["stack1_test2allow"],
         shared_environment["stack2_test1allow"],
         shared_environment["stack2_test2allow"]],
        connection="deny")

    # Validate that Lb services has no access to targets with in
    # same stacks or cross stacks
    validate_lb_service_for_no_access(
        admin_client, shared_environment["stack1_lbcrossstack"], "9090")
    validate_lb_service_for_no_access(
        admin_client, shared_environment["stack1_lbwithinstack"], "9091")

    # Validate that connectivity between linked service is denied within the
    # same stack and  cross stacks
    validate_linked_service(
        admin_client, shared_environment["stack1_servicewithlinks"],
        [shared_environment["stack1_test1allow"]], "99", not_reachable=True)
    validate_linked_service(admin_client,
                            shared_environment["stack1_servicecrosslinks"],
                            [shared_environment["stack2_test2allow"]],
                            "98", linkName="test2allow.test2",
                            not_reachable=True)


def validate_default_network_action_deny_networkpolicy_within_service_for_sk(
        admin_client):
    # Validate that containers of primary services are able to connect with
    # other containers in the same service and containers in other sidekick
    # services
    validate_connectivity_between_container_list(
        admin_client,
        shared_environment["stack2_sidekick"]["p_con1"],
        [shared_environment["stack2_sidekick"]["p_con2"],
         shared_environment["stack2_sidekick"]["s1_con1"],
         shared_environment["stack2_sidekick"]["s1_con2"],
         shared_environment["stack2_sidekick"]["s2_con1"],
         shared_environment["stack2_sidekick"]["s2_con2"]],
        "allow")

    # Validate that containers of sidekick services are able to connect with
    # other containers in the same service and containers in other sidekick
    # services and primary service

    validate_connectivity_between_container_list(
        admin_client,
        shared_environment["stack2_sidekick"]["s1_con1"],
        [shared_environment["stack2_sidekick"]["p_con1"],
         shared_environment["stack2_sidekick"]["p_con2"],
         shared_environment["stack2_sidekick"]["s1_con2"],
         shared_environment["stack2_sidekick"]["s2_con1"],
         shared_environment["stack2_sidekick"]["s2_con2"]],
        "allow")

    validate_connectivity_between_container_list(
        admin_client,
        shared_environment["stack2_sidekick"]["s2_con1"],
        [shared_environment["stack2_sidekick"]["p_con1"],
         shared_environment["stack2_sidekick"]["p_con2"],
         shared_environment["stack2_sidekick"]["s1_con1"],
         shared_environment["stack2_sidekick"]["s1_con1"],
         shared_environment["stack2_sidekick"]["s2_con2"]],
        "allow")


def validate_default_network_action_deny_networkpolicy_within_linked(
        admin_client):
    # Validate that standalone containers are not able reach any
    # service containers
    for container in shared_environment["containers"]:
        validate_connectivity_between_con_to_services(
            admin_client, container,
            [shared_environment["stack1_test2allow"],
             shared_environment["stack2_test4deny"]],
            connection="deny")
    # Validate that containers belonging to a service are not able to
    # communicate with other containers in the same service or different
    # service
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test1allow"],
        [shared_environment["stack1_test1allow"],
         shared_environment["stack1_test2allow"],
         shared_environment["stack2_test1allow"],
         shared_environment["stack2_test2allow"]],
        connection="deny")

    # Validate that Lb services has access to targets with in
    # same stacks
    validate_lb_service(admin_client, admin_client,
                        shared_environment["stack1_lbwithinstack"],
                        "9091",
                        [shared_environment["stack1_test1allow"]])

    # Validate that Lb services has access to targets cross stacks
    validate_lb_service(admin_client, admin_client,
                        shared_environment["stack1_lbcrossstack"],
                        "9090",
                        [shared_environment["stack2_test1allow"]])

    service_with_links = shared_environment["stack1_servicewithlinks"]
    linked_service = [shared_environment["stack1_test1allow"]]
    validate_dna_deny_np_within_linked_for_linked_service(
        admin_client, service_with_links, linked_service, "99")

    service_with_links = shared_environment["stack1_servicecrosslinks"]
    linked_service = [shared_environment["stack2_test1allow"]]
    validate_dna_deny_np_within_linked_for_linked_service(
        admin_client, service_with_links, linked_service, "98", "mylink")


def validate_dna_deny_np_within_linked_for_linked_service(
        admin_client, service_with_links, linked_service, port, linkName=None):

    # Validate that all containers of a service with link has access to
    # the containers of the service that it is linked to
    validate_connectivity_between_services(
        admin_client,
        service_with_links,
        linked_service,
        connection="allow")

    # Validate that all containers of a service that is linked by other service
    # has no access to the containers of the service that it is linked by
    # (s1 -> s2) containers of s2 have no access to s1
    for l_service in linked_service:
        validate_connectivity_between_services(
            admin_client,
            l_service,
            [service_with_links],
            connection="deny")

    # Validate that containers are reachable using their link name
    validate_linked_service(admin_client,
                            service_with_links,
                            linked_service,
                            port,
                            linkName=linkName)


def validate_default_network_action_deny_networkpolicy_within_linked_for_sk(
        admin_client):
    containers = get_service_container_list(
        admin_client, shared_environment["stack1_servicelinktosidekick"])
    # Validate connectivity between containers of linked services to linked
    # service with sidekick
    for con in containers:
        validate_connectivity_between_container_list(
            admin_client,
            con,
            shared_environment["stack2_sidekick"].values(),
            "allow")
    for linked_con in shared_environment["stack2_sidekick"].values():
        for con in containers:
            validate_connectivity_between_containers(
                admin_client, linked_con, con, "deny")


def validate_dna_deny_np_within_linked_for_servicealias(
        admin_client):
    # Validate connectivity between containers of linked services to services
    # linked to webservice
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_linktowebservice"],
        [shared_environment["stack1_test4deny"],
         shared_environment["stack2_test3deny"]],
        connection="allow")

    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test4deny"],
        [shared_environment["stack1_linktowebservice"]],
        connection="deny")

    validate_connectivity_between_services(
        admin_client, shared_environment["stack2_tes34deny"],
        [shared_environment["stack1_linktowebservice"]],
        connection="deny")


@if_network_policy
def test_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_stack)
    validate_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client)


@if_network_policy_within_stack
def test_dna_deny_np_allow_within_stacks_stop_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_within_stack)
    stop_service_instances(client, shared_environment["env"][0],
                           shared_environment["stack1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client)


@if_network_policy_within_stack
def test_dna_deny_np_allow_within_stacks_delete_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_within_stack)
    delete_service_instances(client, shared_environment["env"][0],
                             shared_environment["stack1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client)


@if_network_policy_within_stack
def test_dna_deny_np_allow_within_stacks_restart_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_within_stack)
    restart_service_instances(client, shared_environment["env"][0],
                              shared_environment["stack1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client)


@if_network_policy
def test_default_network_action_deny_networkpolicy_none(admin_client, client):
    set_network_policy(client, "deny")
    validate_default_network_action_deny_networkpolicy_none(
        admin_client)


@if_network_policy_none
def test_dna_deny_np_none_stop_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny")
    stop_service_instances(client, shared_environment["env"][0],
                           shared_environment["stack1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_none(
        admin_client)


@if_network_policy_none
def test_dna_deny_np_none_delete_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny")
    delete_service_instances(client, shared_environment["env"][0],
                             shared_environment["stack1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_none(
        admin_client)


@if_network_policy_none
def test_dna_deny_np_none_restart_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny")
    restart_service_instances(client, shared_environment["env"][0],
                              shared_environment["stack1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_none(
        admin_client)


@if_network_policy
def test_default_network_action_deny_networkpolicy_groupby(
        admin_client, client):
    set_network_policy(client, "deny", policy_groupby)
    validate_default_network_action_deny_networkpolicy_groupby(
        admin_client)


@if_network_policy_groupby
def test_dna_deny_np_groupby_stop_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_groupby)
    stop_service_instances(client, shared_environment["env"][0],
                           shared_environment["stack1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_groupby(
        admin_client)


@if_network_policy_groupby
def test_dna_deny_np_groupby_delete_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_groupby)
    delete_service_instances(client, shared_environment["env"][0],
                             shared_environment["stack1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_groupby(
        admin_client)


@if_network_policy_groupby
def test_dna_deny_np_groupby_restart_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_groupby)
    restart_service_instances(client, shared_environment["env"][0],
                              shared_environment["stack1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_groupby(
        admin_client)


@if_network_policy
def test_default_network_action_deny_networkpolicy_allow_within_service(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_service)
    validate_default_network_action_deny_networkpolicy_within_service(
        admin_client)


@if_network_policy_within_service
def test_dna_deny_np_allow_within_service_delete_service(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_service)
    delete_service_instances(client, shared_environment["env"][0],
                             shared_environment["stack1_test1allow"], [1])
    delete_service_instances(client, shared_environment["env"][0],
                             shared_environment["stack1_lbcrossstack"], [1])
    delete_service_instances(client, shared_environment["env"][0],
                             shared_environment["stack1_lbwithinstack"], [1])
    delete_service_instances(
        client, shared_environment["env"][0],
        shared_environment["stack1_servicewithlinks"], [1])
    validate_default_network_action_deny_networkpolicy_within_service(
        admin_client)


@if_network_policy_within_service
def test_dna_deny_np_allow_within_service_scale_service(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_service)
    scale_service(shared_environment["stack1_test1allow"], client, 3)
    scale_service(shared_environment["stack1_lbcrossstack"], client, 3)
    scale_service(shared_environment["stack1_lbwithinstack"], client, 3)
    scale_service(shared_environment["stack1_servicewithlinks"], client, 3)
    populate_env_details(client)
    validate_default_network_action_deny_networkpolicy_within_service(
        admin_client)
    scale_service(shared_environment["stack1_test1allow"], client, 2)
    scale_service(shared_environment["stack1_lbcrossstack"], client, 2)
    scale_service(shared_environment["stack1_lbwithinstack"], client, 2)
    scale_service(shared_environment["stack1_servicewithlinks"], client, 2)


@if_network_policy_within_service
def test_dna_deny_np_allow_within_service_stop_service(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_service)
    validate_default_network_action_deny_networkpolicy_within_service(
        admin_client)
    stop_service_instances(client, shared_environment["env"][0],
                           shared_environment["stack1_test1allow"], [1])
    stop_service_instances(client, shared_environment["env"][0],
                           shared_environment["stack1_lbcrossstack"], [1])
    stop_service_instances(client, shared_environment["env"][0],
                           shared_environment["stack1_lbwithinstack"], [1])
    stop_service_instances(
        client, shared_environment["env"][0],
        shared_environment["stack1_servicewithlinks"], [1])

    validate_default_network_action_deny_networkpolicy_within_service(
        admin_client)


@if_network_policy
def test_dna_deny_np_allow_within_service_check_sidekicks(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_service)
    validate_default_network_action_deny_networkpolicy_within_service_for_sk(
        admin_client)


@if_network_policy
def test_default_network_action_deny_networkpolicy_allow_within_linked(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_linked)
    validate_default_network_action_deny_networkpolicy_within_linked(
        admin_client)


@if_network_policy
def test_dna_deny_np_allow_within_linked_for_sk(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_linked)
    validate_default_network_action_deny_networkpolicy_within_linked_for_sk(
        admin_client)


@if_network_policy
def test_dna_deny_np_allow_within_linked_for_sa(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_linked)
    validate_dna_deny_np_within_linked_for_servicealias(
        admin_client)


@if_network_policy_within_linked
def test_dna_deny_np_allow_within_linked_after_scaleup(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_linked)

    service_with_links = shared_environment["stack1_servicewithlinks"]
    linked_service = shared_environment["stack1_test1allow"]
    validate_dna_deny_np_within_linked_for_linked_service(
        admin_client, service_with_links, [linked_service], "99")

    scale_service(linked_service, client, 3)
    shared_environment["stack1_test1allow"] = \
        get_service_by_name(client,
                            shared_environment["env"][0],
                            "test1allow")
    linked_service = shared_environment["stack1_test1allow"]

    validate_dna_deny_np_within_linked_for_linked_service(
        admin_client, service_with_links, [linked_service], "99")

    scale_service(linked_service, client, 2)
    shared_environment["stack1_test1allow"] = \
        get_service_by_name(client,
                            shared_environment["env"][0],
                            "test1allow")
    linked_service = shared_environment["stack1_test1allow"]

    scale_service(service_with_links, client, 3)
    shared_environment["stack1_servicewithlinks"] = \
        get_service_by_name(client,
                            shared_environment["env"][0],
                            "servicewithlinks")
    service_with_links = shared_environment["stack1_servicewithlinks"]

    validate_dna_deny_np_within_linked_for_linked_service(
        admin_client, service_with_links, [linked_service], "99")
    scale_service(service_with_links, client, 2)
    shared_environment["stack1_servicewithlinks"] = \
        get_service_by_name(client,
                            shared_environment["env"][0],
                            "servicewithlinks")


@if_network_policy_within_linked
def test_dna_deny_np_allow_within_linked_after_adding_removing_links(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_linked)

    service_with_links = shared_environment["stack1_servicewithlinks"]
    linked_service = [shared_environment["stack1_test1allow"]]
    validate_dna_deny_np_within_linked_for_linked_service(
        admin_client, service_with_links, linked_service, "99")

    # Add another service link
    service_with_links.setservicelinks(
        serviceLinks=[
            {"serviceId": shared_environment["stack1_test1allow"].id},
            {"serviceId": shared_environment["stack1_test2allow"].id}])

    validate_dna_deny_np_within_linked_for_linked_service(
        admin_client, service_with_links,
        [shared_environment["stack1_test1allow"]], "99")
    validate_dna_deny_np_within_linked_for_linked_service(
        admin_client, service_with_links,
        [shared_environment["stack1_test2allow"]], "99")

    # Remove existing service link
    service_with_links.setservicelinks(
        serviceLinks=[
            {"serviceId": shared_environment["stack1_test1allow"].id}])
    linked_service = [shared_environment["stack1_test1allow"]]
    validate_dna_deny_np_within_linked_for_linked_service(
        admin_client, service_with_links, linked_service, "99")
    validate_connectivity_between_services(
        admin_client, service_with_links,
        [shared_environment["stack1_test2allow"]],
        connection="deny")
    validate_connectivity_between_services(
        admin_client, shared_environment["stack1_test2allow"],
        [service_with_links],
        connection="deny")


def scale_service(service, client, final_scale):
    service = client.update(service, name=service.name, scale=final_scale)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_scale
    check_container_in_service(client, service)


def set_network_policy(client, defaultPolicyAction="allow", policy=None):
    networks = client.list_network(name='ipsec')
    assert len(networks) == 1
    network = networks[0]
    network = client.update(
        network, defaultPolicyAction=defaultPolicyAction, policy=policy)
    network = wait_success(client, network)
    assert network.defaultPolicyAction == defaultPolicyAction
    populate_env_details(client)


def check_for_network_policy_manager(client):
    np_manager = False
    env = client.list_stack(name="network-policy-manager")
    if len(env) == 1:
        service = get_service_by_name(client, env[0],
                                      "network-policy-manager")
        if service.state == "active":
            np_manager = True
    return np_manager


def create_standalone_containers(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    cons = []
    cons_with_label = []
    for host in hosts:
        con_name = random_str()
        con = client.create_container(
            name=con_name,
            ports=['3001:22'],
            imageUuid=HEALTH_CHECK_IMAGE_UUID,
            networkMode=MANAGED_NETWORK,
            requestedHostId=host.id)
        con = client.wait_success(con)
        assert con.state == "running"
        cons.append(con)
    shared_environment["containers"] = cons
    for host in hosts:
        con_name = random_str()
        con = client.create_container(
            name=con_name,
            ports=['3002:22'],
            imageUuid=HEALTH_CHECK_IMAGE_UUID,
            networkMode=MANAGED_NETWORK,
            requestedHostId=host.id,
            labels={"com.rancher.stack.location": "east"})
        con = client.wait_success(con)
        assert con.state == "running"
        cons_with_label.append(con)
    shared_environment["containers_with_label"] = cons_with_label
