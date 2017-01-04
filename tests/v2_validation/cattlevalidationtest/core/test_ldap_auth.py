from common_fixtures import *  # NOQA
from requests.auth import AuthBase
from cattle import ApiError, ClientApiError


if_test_ldap = pytest.mark.skipif(not os.environ.get('API_AUTH_LDAP_SERVER'),
                                  reason='API_AUTH_LDAP_SERVER is not set')

if_do_key = pytest.mark.skipif(
    not os.environ.get('DIGITALOCEAN_KEY'),
    reason="Digital Ocean key is not set")

ADMIN_LDAP_CLIENT = None


class LdapAuth(AuthBase):
    def __init__(self, jwt, prj_id=None):
        # setup any auth-related data here
        self.jwt = jwt
        self.prj_id = prj_id

    def __call__(self, r):
        # modify and return the request
        r.headers['Authorization'] = 'Bearer ' + self.jwt
        if self.prj_id is not None:
            r.headers['X-API-Project-Id'] = self.prj_id
        return r


@pytest.fixture(scope='session', autouse=True)
def ldap_client(admin_client):
    key = admin_client.create_apiKey()
    admin_client.wait_success(key)
    ldap_client = from_env(url=cattle_url(),
                           access_key=key.publicValue,
                           secret_key=key.secretValue)
    global ADMIN_LDAP_CLIENT
    ADMIN_LDAP_CLIENT = ldap_client


def create_ldap_client(username=None,
                       password=None,
                       project_id=None):

    client = from_env(url=cattle_url(),
                      access_key=ADMIN_LDAP_CLIENT._access_key,
                      secret_key=ADMIN_LDAP_CLIENT._secret_key)
    client.delete_by_id = delete_by_id
    assert client.valid()
    jwt = get_authed_token(username=username, password=password)['jwt']
    client._access_key = None
    client._secret_key = None

    client._auth = LdapAuth(jwt, prj_id=project_id)
    client.reload_schema()
    assert client.valid()

    identities = client.list_identity()
    assert len(identities) > 0

    return client


def get_authed_token(username=None, password=None):
    token = requests.post(cattle_url() + '/token', {
        'authProvider': "ldapconfig",
        'code': username + ':' + password
    })
    assert token.ok
    token = token.json()
    assert token['type'] != 'error'
    assert token['user'] == username
    assert token['userIdentity']['login'] == username
    return token


def load_config():
    config = {
        'accessMode': 'unrestricted',
        'server': os.environ.get('API_AUTH_LDAP_SERVER'),
        'domain': os.environ.get('API_AUTH_LDAP_SEARCH_BASE'),
        'port': os.environ.get('API_AUTH_LDAP_PORT'),
        'serviceAccountPassword': os.environ.get('API_AUTH_LDAP_'
                                                 'SERVICE_ACCOUNT_PASSWORD'),
        'serviceAccountUsername': os.environ.get('API_AUTH_LDAP_'
                                                 'SERVICE_ACCOUNT_USERNAME'),
        'groupNameField': os.environ.get('SCHEMA_LDAP_GROUP_NAME_FIELD'),
        'groupObjectClass': os.environ.get('SCHEMA_LDAP_GROUP_OBJECT_CLASS'),
        'groupSearchField': os.environ.get('SCHEMA_LDAP_GROUP_SEARCH_FIELD'),
        'groupDNField': os.environ.get('SCHEMA_LDAP_GROUP_DN_FIELD'),
        'groupMemberMappingAttribute': "memberUid",
        'groupMemberUserAttribute': os.environ.get('SCHEMA_LDAP_GROUP_'
                                                   'MEMBER_USER_ATTRIBUTE'),
        'loginDomain': None,
        'enabled': True,
        'tls': False,
        'userDisabledBitMask': os.environ.get('SCHEMA_LDAP_USER_DISABLED'
                                              '_STATUS_BITMASK'),
        'userEnabledAttribute': None,
        'userLoginField': os.environ.get('SCHEMA_LDAP_USER_LOGIN_FIELD'),
        'userNameField': os.environ.get('SCHEMA_LDAP_USER_NAME_FIELD'),
        'userObjectClass': os.environ.get('SCHEMA_LDAP_USER_OBJECT_CLASS'),
        'userSearchField': os.environ.get('SCHEMA_LDAP_USER_SEARCH_FIELD'),
        'userMemberAttribute': "memberOf"

    }
    return config


def idToMember(identity, role):
    return {
        'externalId': identity.externalId,
        'externalIdType': identity.externalIdType,
        'role': role
    }


@pytest.fixture(scope='session', autouse=True)
def turn_on_off_ldap_auth(admin_client, request):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')

    # Disable LDAP Authentication
    config = load_config()
    config['enabled'] = False
    admin_client.create_openldapconfig(config)

    # Get main user token and client
    client = create_ldap_client(username=ldap_main_user,
                                password=ldap_main_pass)

    token = get_authed_token(username=ldap_main_user,
                             password=ldap_main_pass)
    user = token['userIdentity']

    # Enable LDAP Authentication
    allowed_identities = []
    allowed_identities.append(user)
    config['enabled'] = True
    config['allowedIdentities'] = allowed_identities
    admin_client.create_openldapconfig(config)

    def fin():
        config = load_config()
        config['enabled'] = None
        client.create_ldapconfig(config)
    request.addfinalizer(fin)


# 1
@if_test_ldap
def test_allow_any_ldap_user(admin_client):
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    token = get_authed_token(username=ldap_user2,
                             password=ldap_pass2)

    cookies = dict(token=token['jwt'])
    schemas = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert schemas.status_code == 200


# 4
@if_test_ldap
def test_ldap_user_with_new_env(admin_client):
    ldap_user3 = os.environ.get('LDAP_USER3')
    ldap_pass3 = os.environ.get('LDAP_PASS3')
    # test creation of new env with new valid user
    token = get_authed_token(username=ldap_user3,
                             password=ldap_pass3)

    cookies = dict(token=token['jwt'])
    schemas = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert schemas.status_code == 200

    u3_client = create_ldap_client(username=ldap_user3,
                                   password=ldap_pass3)
    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == ldap_user3 + "-Default":
            found = True
            break
    assert found


# 5
@if_test_ldap
def test_ldap_create_new_env(admin_client):
    ldap_user3 = os.environ.get('LDAP_USER3')
    ldap_pass3 = os.environ.get('LDAP_PASS3')

    u3_client = create_ldap_client(username=ldap_user3,
                                   password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u3_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case5'
    project = u3_client.create_project(name=project_name, members=[
        idToMember(u3_identity, 'owner')
    ])

    u3_client.wait_success(project)
    assert u3_client.by_id('project', project.id) is not None

    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
            assert len(p.members) == 1
            assert p['members'][0]['role'] == 'owner'
            break
    assert found


# 6
@if_test_ldap
def test_ldap_create_new_env_add_member(admin_client):
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')
    ldap_user3 = os.environ.get('LDAP_USER3')
    ldap_pass3 = os.environ.get('LDAP_PASS3')

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    u3_client = create_ldap_client(username=ldap_user3,
                                   password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u3_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case6'
    project = u2_client.create_project(name=project_name, members=[
        idToMember(u2_identity, 'owner')
    ])

    u2_client.wait_success(project)
    assert u2_client.by_id('project', project.id) is not None

    projects = u2_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
            assert len(p.members) == 1
            assert p['members'][0]['role'] == 'owner'
            break
    assert found

    # Add new member as member
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'member')
    ]
    project = u2_client.by_id('project', project.id)
    project.setmembers(members=new_members)

    assert u2_client.by_id('project', project.id) is not None
    assert u3_client.by_id('project', project.id) is not None

    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    # Make sure the new user has no privileges
    project = u3_client.by_id('project', project.id)

    with pytest.raises(AttributeError) as excinfo:
        project.setmembers(members=new_members)
    assert "object has no attribute" in str(excinfo.value)


# 7
@if_test_ldap
def test_ldap_create_new_env_add_owner(admin_client):
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    ldap_user3 = os.environ.get('LDAP_USER3')
    ldap_pass3 = os.environ.get('LDAP_PASS3')

    ldap_user4 = os.environ.get('LDAP_USER4')
    ldap_pass4 = os.environ.get('LDAP_PASS4')

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    u3_client = create_ldap_client(username=ldap_user3,
                                   password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u3_identity = obj
            break

    u4_client = create_ldap_client(username=ldap_user4,
                                   password=ldap_pass4)
    u4_identity = None
    for obj in u4_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u4_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case7'
    project = u2_client.create_project(name=project_name, members=[
        idToMember(u2_identity, 'owner')
    ])

    u2_client.wait_success(project)
    assert u2_client.by_id('project', project.id) is not None

    projects = u2_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
            assert len(p.members) == 1
            assert p['members'][0]['role'] == 'owner'
            break
    assert found

    # Add new member as member
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'owner')
    ]
    project = u2_client.by_id('project', project.id)
    project.setmembers(members=new_members)

    assert u2_client.by_id('project', project.id) is not None
    assert u3_client.by_id('project', project.id) is not None

    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    # Make sure the new user has privileges to add new members
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'owner'),
        idToMember(u4_identity, 'member')
    ]
    same_project = u3_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)

    projects = u4_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found


# 8
@if_test_ldap
def test_ldap_create_new_env_add_group_member(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')

    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    group = os.environ.get('LDAP_GROUP')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            main_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case8'
    project = main_client.create_project(name=project_name, members=[
        idToMember(main_identity, 'owner')
    ])

    main_client.wait_success(project)
    assert main_client.by_id('project', project.id) is not None

    # Add new group as member
    group_identity = main_client.list_identity(name=group)[0]
    new_members = [
        idToMember(main_identity, 'owner'),
        idToMember(group_identity, 'member')
    ]
    project = main_client.by_id('project', project.id)
    project.setmembers(members=new_members)

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)

    projects = u2_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    project = u2_client.by_id('project', project.id)

    with pytest.raises(AttributeError) as excinfo:
        project.setmembers(members=new_members)
    assert "object has no attribute" in str(excinfo.value)


# 9
@if_test_ldap
def test_ldap_create_new_env_add_group_owner(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')

    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    group = os.environ.get('LDAP_GROUP')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            main_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case9'
    project = main_client.create_project(name=project_name, members=[
        idToMember(main_identity, 'owner')
    ])

    main_client.wait_success(project)
    assert main_client.by_id('project', project.id) is not None

    # Add new group as owner
    group_identity = main_client.list_identity(name=group)[0]
    new_members = [
        idToMember(main_identity, 'owner'),
        idToMember(group_identity, 'owner')
    ]
    project = main_client.by_id('project', project.id)
    project.setmembers(members=new_members)

    project = main_client.by_id('project', project.id)
    project_member = project.projectMembers()[1]
    assert project_member['name'] == group
    assert project_member['role'] == 'owner'

    # Make sure user2 has the privileges to edit the env
    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    projects = u2_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    project = u2_client.by_id('project', project.id)
    project.setmembers(members=new_members)


# 10
@if_test_ldap
def test_ldap_create_new_env_change_owner_to_member(admin_client):
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    ldap_user3 = os.environ.get('LDAP_USER3')
    ldap_pass3 = os.environ.get('LDAP_PASS3')

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    u3_client = create_ldap_client(username=ldap_user3,
                                   password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u3_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case10'
    project = u2_client.create_project(name=project_name, members=[
        idToMember(u2_identity, 'owner')
    ])

    u2_client.wait_success(project)
    assert u2_client.by_id('project', project.id) is not None

    # Add new member as owner
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'owner')
    ]
    project = u2_client.by_id('project', project.id)
    project.setmembers(members=new_members)

    assert u2_client.by_id('project', project.id) is not None
    assert u3_client.by_id('project', project.id) is not None

    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    # Change owner to member
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'member'),
    ]
    same_project = u2_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)

    same_project = u3_client.by_id('project', project.id)

    with pytest.raises(AttributeError) as excinfo:
        same_project.setmembers(members=new_members)
    assert "object has no attribute" in str(excinfo.value)


# 11
@if_test_ldap
def test_ldap_create_new_env_change_member_to_owner(admin_client):
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    ldap_user3 = os.environ.get('LDAP_USER3')
    ldap_pass3 = os.environ.get('LDAP_PASS3')

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    u3_client = create_ldap_client(username=ldap_user3,
                                   password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u3_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case11'
    project = u2_client.create_project(name=project_name, members=[
        idToMember(u2_identity, 'owner')
    ])

    u2_client.wait_success(project)
    assert u2_client.by_id('project', project.id) is not None

    # Add new member as member
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'member')
    ]
    project = u2_client.by_id('project', project.id)
    project.setmembers(members=new_members)

    assert u2_client.by_id('project', project.id) is not None
    assert u3_client.by_id('project', project.id) is not None

    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    # Change owner to member
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'owner'),
    ]
    same_project = u2_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)

    # Try to delete user2
    new_members = [
        idToMember(u3_identity, 'owner')
    ]
    same_project = u3_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)

    projects = u2_client.list_project()
    found = True
    for p in projects:
        if p['name'] == project_name:
            found = False
    assert found


# 12
@if_test_ldap
def test_ldap_create_new_env_remove_existing_owner(admin_client):
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    ldap_user3 = os.environ.get('LDAP_USER3')
    ldap_pass3 = os.environ.get('LDAP_PASS3')

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    u3_client = create_ldap_client(username=ldap_user3,
                                   password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u3_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case12'
    project = u2_client.create_project(name=project_name, members=[
        idToMember(u2_identity, 'owner')
    ])

    u2_client.wait_success(project)
    assert u2_client.by_id('project', project.id) is not None

    # Add new member as owner
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'owner')
    ]
    project = u2_client.by_id('project', project.id)
    project.setmembers(members=new_members)

    assert u2_client.by_id('project', project.id) is not None
    assert u3_client.by_id('project', project.id) is not None

    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    # Try to delete user3
    new_members = [
        idToMember(u2_identity, 'owner')
    ]
    same_project = u2_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)

    projects = u3_client.list_project()
    found = True
    for p in projects:
        if p['name'] == project_name:
            found = False
    assert found

    with pytest.raises(ApiError) as excinfo:
        u3_client.by_id('project', project.id)

    assert "Not Found" in str(excinfo.value)


# 13
@if_test_ldap
def test_ldap_create_new_env_remove_existing_member(admin_client):
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    ldap_user3 = os.environ.get('LDAP_USER3')
    ldap_pass3 = os.environ.get('LDAP_PASS3')

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    u3_client = create_ldap_client(username=ldap_user3,
                                   password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u3_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case13'
    project = u2_client.create_project(name=project_name, members=[
        idToMember(u2_identity, 'owner')
    ])

    u2_client.wait_success(project)
    assert u2_client.by_id('project', project.id) is not None

    # Add new member as owner
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'member')
    ]
    project = u2_client.by_id('project', project.id)
    project.setmembers(members=new_members)

    assert u2_client.by_id('project', project.id) is not None
    assert u3_client.by_id('project', project.id) is not None

    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    # Try to delete user3
    new_members = [
        idToMember(u2_identity, 'owner')
    ]
    same_project = u2_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)

    projects = u3_client.list_project()
    found = True
    for p in projects:
        if p['name'] == project_name:
            found = False
    assert found

    with pytest.raises(ApiError) as excinfo:
        u3_client.by_id('project', project.id)

    assert "Not Found" in str(excinfo.value)


# 14,15
@if_test_ldap
def test_ldap_deactivate_activate_env(admin_client):
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    ldap_user3 = os.environ.get('LDAP_USER3')
    ldap_pass3 = os.environ.get('LDAP_PASS3')

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    u3_client = create_ldap_client(username=ldap_user3,
                                   password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u3_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case14'
    project = u2_client.create_project(name=project_name, members=[
        idToMember(u2_identity, 'owner')
    ])

    u2_client.wait_success(project)
    assert u2_client.by_id('project', project.id) is not None

    # Add new member as owner
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'member')
    ]
    project = u2_client.by_id('project', project.id)
    project.setmembers(members=new_members)

    assert u2_client.by_id('project', project.id) is not None
    assert u3_client.by_id('project', project.id) is not None

    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    # Deactivate environment
    dec_project = u2_client.by_id('project', project.id)
    dec_project.deactivate()
    dec_project = u2_client.by_id('project', project.id)
    assert dec_project['state'] == 'inactive'

    # Owners should see the env in their "Manage Environment" Tab
    projects = u2_client.list_project(all=True)
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    # Members has no access to the environment
    try:
        project = u3_client.by_id('project', project.id)
    except:
        assert True

    # Activate environment back
    dec_project.activate()
    act_project = u2_client.by_id('project', project.id)
    assert act_project['state'] == 'active'

    assert u3_client.by_id('project', project.id) is not None


# 16
@if_test_ldap
def test_ldap_remove_deactivated_env(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')
    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)

    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    ldap_user3 = os.environ.get('LDAP_USER3')
    ldap_pass3 = os.environ.get('LDAP_PASS3')

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    u3_client = create_ldap_client(username=ldap_user3,
                                   password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u3_identity = obj
            break

    # Creating a new project
    project_name = random_str() + '-test_case16'
    project = u2_client.create_project(name=project_name, members=[
        idToMember(u2_identity, 'owner')
    ])

    u2_client.wait_success(project)
    assert u2_client.by_id('project', project.id) is not None

    # Add new member as owner
    new_members = [
        idToMember(u2_identity, 'owner'),
        idToMember(u3_identity, 'member')
    ]
    project = u2_client.by_id('project', project.id)
    project.setmembers(members=new_members)

    assert u2_client.by_id('project', project.id) is not None
    assert u3_client.by_id('project', project.id) is not None

    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    # Deactivate environment
    dec_project = u2_client.by_id('project', project.id)
    dec_project.deactivate()
    dec_project = u2_client.by_id('project', project.id)
    assert dec_project['state'] == 'inactive'

    # Owners should see the env in their "Manage Environment" Tab
    projects = u2_client.list_project(all=True)
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    # Members has no access to the environment
    try:
        project = u3_client.by_id('project', project.id)
    except:
        assert True

    # Remove environment
    main_client.delete(dec_project)
    time.sleep(5)
    project = main_client.by_id('project', project.id)
    assert project.state == 'purged' or project.state == 'removed'

    # Users can't access the environment anymore
    with pytest.raises(ApiError) as excinfo:
        u2_client.by_id('project', project.id)

    assert "Not Found" in str(excinfo.value)

    with pytest.raises(ApiError) as excinfo:
        u3_client.by_id('project', project.id)
    assert "Not Found" in str(excinfo.value)


# 17,18
@if_test_ldap
def test_ldap_activate_deactivate_account(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)

    u2_token = get_authed_token(username=ldap_user2,
                                password=ldap_pass2)

    # Deactivate the user2 account
    ldap_u2_name = u2_token['userIdentity']['name']
    u2_account = main_client.list_account(name=ldap_u2_name)[0]
    u2_account = main_client.by_id("account", u2_account.id)
    u2_account.deactivate()
    main_client.wait_success(u2_account)

    cookies = dict(token=u2_token['jwt'])
    bad_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert bad_auth.status_code == 401

    # Active the user1 account
    u2_account = main_client.by_id("account", u2_account.id)
    u2_account.activate()
    main_client.wait_success(u2_account)

    cookies = dict(token=u2_token['jwt'])
    good_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert good_auth.status_code == 200


# 19
@if_test_ldap
def test_ldap_purge_account(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')
    ldap_user2 = os.environ.get('LDAP_USER4')
    ldap_pass2 = os.environ.get('LDAP_PASS4')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)

    u2_token = get_authed_token(username=ldap_user2,
                                password=ldap_pass2)
    u2_name = u2_token['userIdentity']['name']

    # Purge user2 account
    u2_account = main_client.list_account(name=u2_name)[0]
    u2_account = main_client.by_id("account", u2_account.id)
    u2_account.deactivate()
    main_client.wait_success(u2_account)
    main_client.delete(u2_account)

    u2_account = main_client.wait_success(u2_account)
    u2_account.purge()
    main_client.wait_success(u2_account)
    assert u2_account.removed is not None

    projects = main_client.list_project(all=True)
    for p in projects:
        project = main_client.by_id('project', p.id)
        project_members = project.projectMembers()
        for project_member in project_members:
            if project_member['name'] == u2_name:
                assert False


# 23,24,25,26,27
@if_test_ldap
def test_ldap_member_permissions(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)

    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            main_identity = obj
            break

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    # Create new env
    project_name = random_str() + '-test_case23'
    project = main_client.create_project(name=project_name, members=[
        idToMember(main_identity, 'owner'),
        idToMember(u2_identity, 'member')
    ])

    main_client.wait_success(project)
    assert main_client.by_id('project', project.id) is not None
    assert u2_client.by_id('project', project.id) is not None

    # user2 can not change, remove, or add users
    new_members = [
        idToMember(main_identity, 'member'),
        idToMember(u2_identity, 'owner')
    ]
    member_project = u2_client.by_id('project', project.id)
    with pytest.raises(AttributeError) as excinfo:
        member_project.setmembers(members=new_members)
    assert "object has no attribute" in str(excinfo.value)

    # user2 can't deactivate or remove environment
    try:
        dec_project = u2_client.by_id('project', project.id)
        dec_project.deactivate()
        dec_project = u2_client.by_id('project', project.id)
        assert dec_project['state'] == 'inactive'
        user1_client.delete(dec_project)
        time.sleep(5)
        project = user1_client.by_id('project', project.id)
        assert project.state == 'purged' or project.state == 'removed'
        assert False
    except:
        assert True


# 28
@if_test_ldap
def test_ldap_change_user_to_admin(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)

    # Purge user2 account first
    u2_token = get_authed_token(username=ldap_user2,
                                password=ldap_pass2)
    u2_name = u2_token['userIdentity']['name']
    u2_account = main_client.list_account(name=u2_name)[0]
    u2_account = main_client.by_id("account", u2_account.id)
    u2_account.deactivate()
    main_client.wait_success(u2_account)
    main_client.delete(u2_account)

    u2_account = main_client.wait_success(u2_account)
    u2_account.purge()
    main_client.wait_success(u2_account)
    assert u2_account.removed is not None

    # Test with user
    u2_token = get_authed_token(username=ldap_user2,
                                password=ldap_pass2)
    u2_name = u2_token['userIdentity']['name']
    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)

    with pytest.raises(ClientApiError) as excinfo:
        u2_client.list_ldapconfig()
    assert "is not a valid type" in str(excinfo.value)

    # change account from user to admin
    u2_account = main_client.list_account(name=u2_name)[0]
    u2_account = main_client.by_id("account", u2_account.id)
    main_client.wait_success(u2_account)
    main_client.update_by_id_account(u2_account.id, kind='admin')

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    assert u2_client.list_ldapconfig() is not None

    # change account from admin to user
    u2_account = main_client.list_account(name=u2_name)[0]
    u2_account = main_client.by_id("account", u2_account.id)
    main_client.wait_success(u2_account)
    main_client.update_by_id_account(u2_account.id, kind='user')


# 29
@if_test_ldap
def test_ldap_admin_list_all_env(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)

    # Purge user2 account first
    u2_token = get_authed_token(username=ldap_user2,
                                password=ldap_pass2)
    u2_name = u2_token['userIdentity']['name']
    u2_account = main_client.list_account(name=u2_name)[0]
    u2_account = main_client.by_id("account", u2_account.id)
    u2_account.deactivate()
    main_client.wait_success(u2_account)
    main_client.delete(u2_account)

    u2_account = main_client.wait_success(u2_account)
    u2_account.purge()
    main_client.wait_success(u2_account)
    assert u2_account.removed is not None

    u2_token = get_authed_token(username=ldap_user2,
                                password=ldap_pass2)
    u2_name = u2_token['userIdentity']['name']

    # change account from user to admin
    u2_account = main_client.list_account(name=u2_name)[0]
    u2_account = main_client.by_id("account", u2_account.id)
    main_client.wait_success(u2_account)
    main_client.update_by_id_account(u2_account.id, kind='admin')

    # List all projects
    projects = main_client.list_project()

    # Create new project
    main_client.create_project()

    for project in projects:
        project_url = cattle_url() \
                      + "/projects/" + project.id + "/projectmembers"
        cookies = dict(token=u2_token['jwt'])
        access = requests.get(project_url, cookies=cookies)
        assert access.ok

    # change account from admin to user
    u2_account = main_client.list_account(name=u2_name)[0]
    u2_account = main_client.by_id("account", u2_account.id)
    main_client.wait_success(u2_account)
    main_client.update_by_id_account(u2_account.id, kind='user')


# 30
@if_test_ldap
@if_do_key
def test_ldap_member_add_host(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            main_identity = obj
            break

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    # test creation of new env
    project = main_client.create_project(members=[
        idToMember(main_identity, 'owner'),
        idToMember(u2_identity, 'member')
    ])

    main_client.wait_success(project)
    assert main_client.by_id('project', project.id) is not None
    assert u2_client.by_id('project', project.id) is not None

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2,
                                   project_id=project.id)
    # Add new host
    host_list = \
        add_digital_ocean_hosts(
            u2_client, 1)
    assert len(host_list) == 1

    # Remove host
    host = host_list[0]
    deactivated_host = host.deactivate()
    u2_client.wait_success(deactivated_host)

    deactivated_host.remove()

    all_hosts = u2_client.list_host()
    for h in all_hosts:
        if h.hostname == host.hostname:
            assert False


# 31
@if_test_ldap
@if_do_key
def test_ldap_create_new_env_with_restricted_member(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            main_identity = obj
            break

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    # test creation of new env
    default_prj_id = main_client.list_project(name='Default')[0].id
    default_project = main_client.by_id('project', default_prj_id)
    default_project.setmembers(members=[
        idToMember(main_identity, 'owner'),
        idToMember(u2_identity, 'restricted')
    ])

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2,
                                   project_id=default_prj_id)
    # Add new host
    with pytest.raises(AttributeError) as excinfo:
        host_list = \
            add_digital_ocean_hosts(
                u2_client, 1)
        assert len(host_list) == 1

    assert "object has no attribute" in str(excinfo.value)


# 32
@if_test_ldap
def test_ldap_create_service_with_restricted_member(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            main_identity = obj
            break

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    # test creation of new env
    default_prj_id = main_client.list_project(name='Default')[0].id
    default_project = main_client.by_id('project', default_prj_id)
    default_project.setmembers(members=[
        idToMember(main_identity, 'owner'),
        idToMember(u2_identity, 'restricted')
    ])

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass,
                                     project_id=default_prj_id)

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2,
                                   project_id=default_prj_id)
    # Add new host
    hosts = u2_client.list_host(
                kind='docker', removed_null=True, state="active")
    if len(hosts) == 0:
        host_list = \
            add_digital_ocean_hosts(
                main_client, 1)
        assert len(host_list) == 1

    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    scale = 1
    create_env_and_svc(u2_client, launch_config, scale)


# 33,34
@if_test_ldap
def test_ldap_create_new_env_with_readonly_member(admin_client):
    ldap_main_user = os.environ.get('LDAP_MAIN_USER')
    ldap_main_pass = os.environ.get('LDAP_MAIN_PASS')
    ldap_user2 = os.environ.get('LDAP_USER2')
    ldap_pass2 = os.environ.get('LDAP_PASS2')

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            main_identity = obj
            break

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'openldap_user':
            u2_identity = obj
            break

    # test creation of new env
    default_prj_id = main_client.list_project(name='Default')[0].id
    default_project = main_client.by_id('project', default_prj_id)
    default_project.setmembers(members=[
        idToMember(main_identity, 'owner'),
        idToMember(u2_identity, 'readonly')
    ])

    u2_client = create_ldap_client(username=ldap_user2,
                                   password=ldap_pass2,
                                   project_id=default_prj_id)

    main_client = create_ldap_client(username=ldap_main_user,
                                     password=ldap_main_pass,
                                     project_id=default_prj_id)
    # Add new host
    with pytest.raises(AttributeError) as excinfo:
        host_list = \
            add_digital_ocean_hosts(
                u2_client, 1)
        assert len(host_list) == 1

    assert "object has no attribute" in str(excinfo.value)

    with pytest.raises(AttributeError) as excinfo:
        launch_config = {"imageUuid": TEST_IMAGE_UUID}
        scale = 1
        create_env_and_svc(u2_client, launch_config, scale)

    assert "object has no attribute" in str(excinfo.value)

    # Create service using main client
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    scale = 1
    service, env = create_env_and_svc(main_client, launch_config, scale)

    # List service using user1 client
    service = u2_client.list_service(name=service.name,
                                     stackId=env.id,
                                     removed_null=True)
    assert len(service) == 1
