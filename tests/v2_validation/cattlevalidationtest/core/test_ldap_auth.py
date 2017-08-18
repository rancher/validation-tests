from common_fixtures import *  # NOQA
from requests.auth import AuthBase
import ast

if_test_ad = pytest.mark.skipif(not os.environ.get('API_AUTH_AD_SERVER'),
                                reason='API_AUTH_AD_SERVER is not set')

if_do_key = pytest.mark.skipif(
    not os.environ.get('DIGITALOCEAN_KEY'),
    reason="Digital Ocean key is not set")

if_ldap_port = pytest.mark.skipif(
    os.environ.get('LDAP_PORT') != 'True',
    reason="LDAP_PORT is not True")

ADMIN_AD_CLIENT = None
ADMIN_TOKEN = None


class AdAuth(AuthBase):
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
def ad_client(admin_client):
    key = admin_client.create_apiKey()
    admin_client.wait_success(key)
    ad_client = from_env(url=cattle_url(),
                         access_key=key.publicValue,
                         secret_key=key.secretValue)
    global ADMIN_AD_CLIENT
    ADMIN_AD_CLIENT = ad_client


def create_ad_client(username=None,
                     password=None,
                     project_id=None):

    client = from_env(url=cattle_url(),
                      access_key=ADMIN_AD_CLIENT._access_key,
                      secret_key=ADMIN_AD_CLIENT._secret_key)
    client.delete_by_id = delete_by_id
    assert client.valid()
    jwt = get_authed_token(username=username, password=password)['jwt']
    client._access_key = None
    client._secret_key = None

    client._auth = AdAuth(jwt, prj_id=project_id)
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


def delete_ldap_token(id, cookies):
    response = requests.delete(cattle_url() + '/token/' + id, cookies=cookies)
    assert response.status_code == 204
    for c in response.cookies:
        assert c.name != "token"
    assert "token=;Path=/;Expires=Thu, 01 Jan 1970 00:00:00 GMT;" \
        in response.headers['set-cookie']


def load_config(access_mode="unrestricted"):
    if os.environ.get('API_AUTH_AD_TLS') == 'True':
        tls = True
    else:
        tls = False
    config = {
        'server': os.environ.get('API_AUTH_AD_SERVER'),
        'domain': os.environ.get('API_AUTH_AD_SEARCH_BASE'),
        'loginDomain': os.environ.get('API_AUTH_AD_LOGIN_DOMAIN'),
        'port': int(os.environ.get('API_AUTH_AD_PORT')),
        'serviceAccountPassword': os.environ.get('API_AUTH_AD_'
                                                 'SERVICE_ACCOUNT_PASSWORD'),
        'serviceAccountUsername': os.environ.get('API_AUTH_AD_'
                                                 'SERVICE_ACCOUNT_USERNAME'),
        'groupNameField': os.environ.get('SCHEMA_AD_GROUP_NAME_FIELD'),
        'groupObjectClass': os.environ.get('SCHEMA_AD_GROUP_OBJECT_CLASS'),
        'groupSearchField': os.environ.get('SCHEMA_AD_GROUP_SEARCH_FIELD'),
        'groupDNField': os.environ.get('SCHEMA_AD_GROUP_DN_FIELD'),
        'tls': tls,
        'groupMemberMappingAttribute': "memberUid",
        'groupMemberUserAttribute': os.environ.get('SCHEMA_AD_GROUP_'
                                                   'MEMBER_USER_ATTRIBUTE'),
        'groupSearchDomain': os.environ.get('API_AUTH_AD_GROUP_SEARCH_BASE'),

        'userDisabledBitMask': int(os.environ.get('SCHEMA_AD_USER_DISABLED'
                                                  '_STATUS_BITMASK')),
        'userEnabledAttribute': None,
        'userLoginField': os.environ.get('SCHEMA_AD_USER_LOGIN_FIELD'),
        'userNameField': os.environ.get('SCHEMA_AD_USER_NAME_FIELD'),
        'userObjectClass': os.environ.get('SCHEMA_AD_USER_OBJECT_CLASS'),
        'userSearchField': os.environ.get('SCHEMA_AD_USER_SEARCH_FIELD'),
        'userMemberAttribute': "memberOf"
    }

    ldap_port = os.environ.get('LDAP_PORT')
    if ldap_port == 'True':
        data = {
            "accessMode": access_mode,
            "allowedIdentities": [],
            "enabled": True,
            "provider": "ldapconfig",
            "ldapconfig": config,
            "githubConfig": {},
            "shibbolethConfig": {},
            "type": "config"
        }
    else:
        config['accessMode'] = access_mode
        config['enabled'] = True
        return config

    return data


def load_test_api_config(auth_config):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    config = {
        "authConfig": auth_config,
        "code": ldap_main_user + ":" + ldap_main_pass,
        "type": "testAuthConfig"
    }
    return config


def idToMember(identity, role):
    return {
        'externalId': identity.externalId,
        'externalIdType': identity.externalIdType,
        'role': role
    }


@pytest.fixture(scope='session', autouse=True)
def turn_on_off_ad_auth(admin_client, request):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')

    # Disable AD Authentication
    config = load_config()
    config['enabled'] = False

    ldap_port = os.environ.get('LDAP_PORT')
    if ldap_port == 'True':
        auth_url = cattle_url()[:-7] + 'v1-auth/config'
        r = requests.post(auth_url, data=json.dumps(config))
        assert r.ok
    else:
        admin_client.create_ldapconfig(config)

    token = get_authed_token(username=ldap_main_user,
                             password=ldap_main_pass)
    user = token['userIdentity']
    global ADMIN_TOKEN
    ADMIN_TOKEN = token

    # Enable AD Authentication
    allowed_identities = []
    allowed_identities.append(user)
    config['enabled'] = True
    config['allowedIdentities'] = allowed_identities

    if ldap_port == 'True':
        auth_url = cattle_url()[:-7] + 'v1-auth/config'
        r = requests.post(auth_url, data=json.dumps(config))
        assert r.ok
    else:
        admin_client.create_ldapconfig(config)

    def fin():
        config = load_config()
        config['enabled'] = None
        access_key = ADMIN_AD_CLIENT._access_key
        secret_key = ADMIN_AD_CLIENT._secret_key
        ldap_port = os.environ.get('LDAP_PORT')
        if ldap_port == 'True':
            auth_url = cattle_url()[:-7] + 'v1-auth/config'
            r = requests.post(auth_url, data=json.dumps(config),
                              auth=(access_key, secret_key))
            assert r.ok
        else:
            client = create_ad_client(username=ldap_main_user,
                                      password=ldap_main_pass)
            client.create_ldapconfig(config)
    request.addfinalizer(fin)


def reconfigure_ad(admin_client, domain, groupSearchDomain):
    # Use testlogin api
    ldap_port = os.environ.get('LDAP_PORT')
    if ldap_port == 'True':
        auth_config = load_config()
        auth_config['ldapconfig']['domain'] = domain
        auth_config['ldapconfig']['groupSearchDomain'] = groupSearchDomain
        test_config = load_test_api_config(auth_config)
        access_key = ADMIN_AD_CLIENT._access_key
        secret_key = ADMIN_AD_CLIENT._secret_key
        auth_url = cattle_url()[:-7] + 'v1-auth/testlogin'
        r = requests.post(auth_url, data=json.dumps(test_config),
                          auth=(access_key, secret_key))
        assert r.ok
        config = load_config()
        config['ldapconfig']['domain'] = domain
        config['ldapconfig']['groupSearchDomain'] = groupSearchDomain
        auth_url = cattle_url()[:-7] + 'v1-auth/config'
        r = requests.post(auth_url, data=json.dumps(config),
                          auth=(access_key, secret_key))
        assert r.ok
        return

    config = load_config()
    config['enabled'] = None
    admin_client.create_ldapconfig(config)
    user = ADMIN_TOKEN['userIdentity']
    allowed_identities = []
    allowed_identities.append(user)
    config['enabled'] = True
    config['allowedIdentities'] = allowed_identities
    config['domain'] = domain
    config['groupSearchDomain'] = groupSearchDomain
    admin_client.create_ldapconfig(config)
    return admin_client


# 1
@if_test_ad
def test_allow_any_ad_user(admin_client):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    token = get_authed_token(username=ldap_user2,
                             password=ldap_pass2)

    cookies = dict(token=token['jwt'])
    schemas = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert schemas.status_code == 200


@if_test_ad
def test_ad_delete_token_on_logout(admin_client):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    token = get_authed_token(username=ldap_user2,
                             password=ldap_pass2)

    cookies = dict(token=token['jwt'])
    identities = requests.get(cattle_url() + "identities", cookies=cookies)
    assert identities.status_code == 200

    delete_ldap_token("current", cookies)

    identities = requests.get(cattle_url() + "identities", cookies=cookies)
    assert identities.status_code == 401


# 4
@if_test_ad
def test_ad_user_with_new_env(admin_client):
    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')
    # test creation of new env with new valid user
    token = get_authed_token(username=ldap_user3,
                             password=ldap_pass3)

    cookies = dict(token=token['jwt'])
    schemas = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert schemas.status_code == 200

    u3_client = create_ad_client(username=ldap_user3,
                                 password=ldap_pass3)
    projects = u3_client.list_project()
    found = False
    for p in projects:
        if p['name'] == ldap_user3 + "-Default":
            found = True
            break
    assert found


# 5
@if_test_ad
def test_ad_create_new_env(admin_client):
    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')

    u3_client = create_ad_client(username=ldap_user3,
                                 password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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
@if_test_ad
def test_ad_create_new_env_add_member(admin_client):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')
    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    u3_client = create_ad_client(username=ldap_user3,
                                 password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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
@if_test_ad
def test_ad_create_new_env_add_owner(admin_client):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')

    ldap_user4 = os.environ.get('AD_USER4')
    ldap_pass4 = os.environ.get('AD_PASS4')

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    u3_client = create_ad_client(username=ldap_user3,
                                 password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u3_identity = obj
            break

    u4_client = create_ad_client(username=ldap_user4,
                                 password=ldap_pass4)
    u4_identity = None
    for obj in u4_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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
@if_test_ad
def test_ad_create_new_env_add_group_member(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')

    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    group = os.environ.get('AD_GROUP')

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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

    u2_client = create_ad_client(username=ldap_user2,
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
@if_test_ad
def test_ad_create_new_env_add_group_owner(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')

    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    group = os.environ.get('AD_GROUP')

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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
    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    projects = u2_client.list_project()
    found = False
    for p in projects:
        if p['name'] == project_name:
            found = True
    assert found

    project = u2_client.by_id('project', project.id)
    project.setmembers(members=new_members)


@if_test_ad
def test_ad_group_search_domain(admin_client, request):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    group = os.environ.get('AD_GROUP')
    group_search_domain = os.environ.get('API_AUTH_AD_GROUP_SEARCH_BASE')
    narrow_domain = os.environ.get('API_AUTH_AD_NARROW_SEARCH_BASE')

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)

    # Narrow down domain to OU=Domain Controllers,
    # and don't set group_search_domain so that group search fails
    reconfigure_ad(main_client, narrow_domain, '')
    assert len(main_client.list_identity(name=group)) == 0

    # Set groupSearchDomain so group search works
    reconfigure_ad(main_client, narrow_domain, group_search_domain)
    assert len(main_client.list_identity(name=group)) == 1
    assert main_client.list_identity(name=group)[0]['login'] == group

    def fin():
            reconfigure_ad(main_client,
                           os.environ.get('API_AUTH_AD_SEARCH_BASE'), '')

    request.addfinalizer(fin)


# 10
@if_test_ad
def test_ad_create_new_env_change_owner_to_member(admin_client):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    u3_client = create_ad_client(username=ldap_user3,
                                 password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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
@if_test_ad
def test_ad_create_new_env_change_member_to_owner(admin_client):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    u3_client = create_ad_client(username=ldap_user3,
                                 password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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
@if_test_ad
def test_ad_create_new_env_remove_existing_owner(admin_client):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    u3_client = create_ad_client(username=ldap_user3,
                                 password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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

    assert u3_client.by_id('project', project.id) is None


# 13
@if_test_ad
def test_ad_create_new_env_remove_existing_member(admin_client):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    u3_client = create_ad_client(username=ldap_user3,
                                 password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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

    assert u3_client.by_id('project', project.id) is None


# 14,15
@if_test_ad
def test_ad_deactivate_activate_env(admin_client):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    u3_client = create_ad_client(username=ldap_user3,
                                 password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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
    act_project = u2_client.by_id('project', dec_project.id)
    assert act_project['state'] == 'active'

    assert u3_client.by_id('project', dec_project.id) is not None


# 16
@if_test_ad
def test_ad_remove_deactivated_env(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)

    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    u3_client = create_ad_client(username=ldap_user3,
                                 password=ldap_pass3)
    u3_identity = None
    for obj in u3_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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
    project = main_client.by_id('project', dec_project.id)
    assert project.state == 'purged' or project.state == 'removed'

    # Users can't access the environment anymore

    assert u2_client.by_id('project', project.id) is None

    assert u3_client.by_id('project', project.id) is None


# 17,18
@if_test_ad
def test_ad_activate_deactivate_account(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    main_client = create_ad_client(username=ldap_main_user,
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
@if_test_ad
def test_ad_purge_account(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER4')
    ldap_pass2 = os.environ.get('AD_PASS4')

    main_client = create_ad_client(username=ldap_main_user,
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
@if_test_ad
def test_ad_member_permissions(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)

    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            main_identity = obj
            break

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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
@if_test_ad
def test_ad_change_user_to_admin(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    main_client = create_ad_client(username=ldap_main_user,
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
    cookies = dict(token=u2_token['jwt'])
    no_admin = requests.get(cattle_url()[:-7] +
                            'v2-beta/settings/settings.public',
                            cookies=cookies)
    assert not no_admin.ok

    u2_name = u2_token['userIdentity']['name']

    # change account from user to admin
    u2_account = main_client.list_account(name=u2_name)[0]
    u2_account = main_client.by_id("account", u2_account.id)
    main_client.wait_success(u2_account)
    main_client.update_by_id_account(u2_account.id, kind='admin')

    admin = requests.get(cattle_url()[:-7] +
                         'v2-beta/settings/settings.public',
                         cookies=cookies)

    assert admin.ok
    # change account from admin to user
    u2_account = main_client.list_account(name=u2_name)[0]
    u2_account = main_client.by_id("account", u2_account.id)
    main_client.wait_success(u2_account)
    main_client.update_by_id_account(u2_account.id, kind='user')


# 29
@if_test_ad
def test_ad_admin_list_all_env(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    main_client = create_ad_client(username=ldap_main_user,
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
@if_test_ad
@if_do_key
def test_ad_member_add_host(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            main_identity = obj
            break

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
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

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2,
                                 project_id=project.id)
    # Add new host
    host_list = \
        add_digital_ocean_hosts(
            u2_client, 1)
    assert len(host_list) == 1

    # Remove host
    host = u2_client.list_host()[0]
    deactivated_host = host.deactivate()
    u2_client.wait_success(deactivated_host)

    deactivated_host = u2_client.list_host()[0]
    deactivated_host.remove()

    time.sleep(60)

    all_hosts = u2_client.list_host()
    for h in all_hosts:
        if h.hostname == host.hostname:
            assert False


# 31
@if_test_ad
@if_do_key
def test_ad_create_new_env_with_restricted_member(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            main_identity = obj
            break

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    # test creation of new env
    default_prj_id = main_client.list_project(name='Default')[0].id
    default_project = main_client.by_id('project', default_prj_id)
    default_project.setmembers(members=[
        idToMember(main_identity, 'owner'),
        idToMember(u2_identity, 'restricted')
    ])

    u2_client = create_ad_client(username=ldap_user2,
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
@if_test_ad
@if_do_key
def test_ad_create_service_with_restricted_member(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            main_identity = obj
            break

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    # test creation of new env
    default_prj_id = main_client.list_project(name='Default')[0].id
    default_project = main_client.by_id('project', default_prj_id)
    default_project.setmembers(members=[
        idToMember(main_identity, 'owner'),
        idToMember(u2_identity, 'restricted')
    ])

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass,
                                   project_id=default_prj_id)

    u2_client = create_ad_client(username=ldap_user2,
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
@if_test_ad
@if_do_key
def test_ad_create_new_env_with_readonly_member(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            main_identity = obj
            break

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2)
    u2_identity = None
    for obj in u2_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            u2_identity = obj
            break

    # test creation of new env
    default_prj_id = main_client.list_project(name='Default')[0].id
    default_project = main_client.by_id('project', default_prj_id)
    default_project.setmembers(members=[
        idToMember(main_identity, 'owner'),
        idToMember(u2_identity, 'readonly')
    ])

    u2_client = create_ad_client(username=ldap_user2,
                                 password=ldap_pass2,
                                 project_id=default_prj_id)

    main_client = create_ad_client(username=ldap_main_user,
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


@if_test_ad
def test_ad_list_identities(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)

    identities = main_client.list_identity()

    user_found = 0
    authenticated_user = 0

    for i in range(len(identities)):
        if identities[i]['user'] is True:
            user_found += 1
            if identities[i]['externalIdType'] != 'rancher_id':
                authenticated_user += 1

    assert user_found == 2
    assert authenticated_user == 1


@if_test_ad
@if_ldap_port
def test_secret_setting(admin_client):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')

    client = create_ad_client(username=ldap_main_user,
                              password=ldap_main_pass)
    secret = client.by_id_setting('api.auth.ldap.service.account.password')
    assert secret.value is None


# 2
@if_test_ad
def test_ad_required_to_specific_user(admin_client, request):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')
    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')
    ldap_user5 = os.environ.get('AD_USER5')
    ldap_pass5 = os.environ.get('AD_PASS5')
    ldap_port = os.environ.get('LDAP_PORT')

    # login with user5 to create a new environment
    get_authed_token(username=ldap_user5,
                     password=ldap_pass5)

    user = ADMIN_TOKEN['userIdentity']
    allowed_identities = []
    allowed_identities.append(user)
    user2_identity = ADMIN_AD_CLIENT.list_identity(name=ldap_user2)[0]
    user2_identity = ast.literal_eval(str(user2_identity))
    allowed_identities.append(user2_identity)

    # Enable new configuration
    config = load_config(access_mode='required')
    config['enabled'] = True
    config['allowedIdentities'] = allowed_identities

    if ldap_port == 'True':
        access_key = ADMIN_AD_CLIENT._access_key
        secret_key = ADMIN_AD_CLIENT._secret_key
        auth_url = cattle_url()[:-7] + 'v1-auth/config'
        r = requests.post(auth_url, data=json.dumps(config),
                          auth=(access_key, secret_key))
        assert r.ok
    else:
        ADMIN_AD_CLIENT.create_ldapconfig(config)

    # Try to login with user2 and user3
    token2 = get_authed_token(username=ldap_user2,
                              password=ldap_pass2)
    try:
        get_authed_token(username=ldap_user3,
                         password=ldap_pass3)
    except AssertionError as e:
        assert '401' in str(e)

    try:
        get_authed_token(username=ldap_user5,
                         password=ldap_pass5)
    except AssertionError as e:
        assert '401' in str(e)

    cookies = dict(token=token2['jwt'])
    good_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert good_auth.status_code == 200

    def fin():
        reconfigure_ad(ADMIN_AD_CLIENT,
                       os.environ.get('API_AUTH_AD_SEARCH_BASE'), '')
    request.addfinalizer(fin)


# 3
@if_test_ad
def test_ad_required_to_specific_group(admin_client, request):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')
    ldap_user3 = os.environ.get('AD_USER3')
    ldap_pass3 = os.environ.get('AD_PASS3')
    ldap_user5 = os.environ.get('AD_USER5')
    ldap_pass5 = os.environ.get('AD_PASS5')
    ldap_port = os.environ.get('LDAP_PORT')
    group = os.environ.get('AD_GROUP')

    # login with user5 to create a new environment
    get_authed_token(username=ldap_user5,
                     password=ldap_pass5)

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)
    user = ADMIN_TOKEN['userIdentity']
    allowed_identities = []
    allowed_identities.append(user)

    group_identity = main_client.list_identity(name=group)[0]
    group_identity_dict = ast.literal_eval(str(group_identity))
    allowed_identities.append(group_identity_dict)

    # Enable new configuration
    config = load_config(access_mode='required')
    config['enabled'] = True
    config['allowedIdentities'] = allowed_identities
    if ldap_port == 'True':
        access_key = ADMIN_AD_CLIENT._access_key
        secret_key = ADMIN_AD_CLIENT._secret_key
        auth_url = cattle_url()[:-7] + 'v1-auth/config'
        r = requests.post(auth_url, data=json.dumps(config),
                          auth=(access_key, secret_key))
        assert r.ok
    else:
        ADMIN_AD_CLIENT.create_ldapconfig(config)

    # Try to login with user2 and user3
    token2 = get_authed_token(username=ldap_user2,
                              password=ldap_pass2)
    try:
        get_authed_token(username=ldap_user3,
                         password=ldap_pass3)
    except AssertionError as e:
        assert '401' in str(e)

    try:
        get_authed_token(username=ldap_user5,
                         password=ldap_pass5)
    except AssertionError as e:
        assert '401' in str(e)

    cookies = dict(token=token2['jwt'])
    good_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert good_auth.status_code == 200

    def fin():
        reconfigure_ad(ADMIN_AD_CLIENT,
                       os.environ.get('API_AUTH_AD_SEARCH_BASE'), '')
    request.addfinalizer(fin)


# 35
@if_test_ad
def test_ad_restricted_to_specific_user(admin_client, request):
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')
    ldap_user3 = os.environ.get('AD_USER6')
    ldap_pass3 = os.environ.get('AD_PASS6')
    ldap_user5 = os.environ.get('AD_USER5')
    ldap_pass5 = os.environ.get('AD_PASS5')
    ldap_port = os.environ.get('LDAP_PORT')

    # login with user5 to create a new environment
    get_authed_token(username=ldap_user5,
                     password=ldap_pass5)

    user = ADMIN_TOKEN['userIdentity']
    allowed_identities = []
    allowed_identities.append(user)
    user2_identity = ADMIN_AD_CLIENT.list_identity(name=ldap_user2)[0]
    user2_identity = ast.literal_eval(str(user2_identity))
    allowed_identities.append(user2_identity)

    # Enable new configuration
    config = load_config(access_mode='restricted')
    config['enabled'] = True
    config['allowedIdentities'] = allowed_identities

    if ldap_port == 'True':
        access_key = ADMIN_AD_CLIENT._access_key
        secret_key = ADMIN_AD_CLIENT._secret_key
        auth_url = cattle_url()[:-7] + 'v1-auth/config'
        r = requests.post(auth_url, data=json.dumps(config),
                          auth=(access_key, secret_key))
        assert r.ok
    else:
        ADMIN_AD_CLIENT.create_ldapconfig(config)

    # Try to login with user2 and user3
    token2 = get_authed_token(username=ldap_user2,
                              password=ldap_pass2)
    try:
        get_authed_token(username=ldap_user3,
                         password=ldap_pass3)
    except AssertionError as e:
        assert '401' in str(e)

    token5 = get_authed_token(username=ldap_user5,
                              password=ldap_pass5)

    cookies = dict(token=token2['jwt'])
    good_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert good_auth.status_code == 200

    cookies = dict(token=token5['jwt'])
    good_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert good_auth.status_code == 200

    def fin():
        reconfigure_ad(ADMIN_AD_CLIENT,
                       os.environ.get('API_AUTH_AD_SEARCH_BASE'), '')
    request.addfinalizer(fin)


# 36
@if_test_ad
def test_ad_restricted_to_specific_group(admin_client, request):
    ldap_main_user = os.environ.get('AD_MAIN_USER')
    ldap_main_pass = os.environ.get('AD_MAIN_PASS')
    ldap_user2 = os.environ.get('AD_USER2')
    ldap_pass2 = os.environ.get('AD_PASS2')
    ldap_user3 = os.environ.get('AD_USER6')
    ldap_pass3 = os.environ.get('AD_PASS6')
    ldap_user5 = os.environ.get('AD_USER5')
    ldap_pass5 = os.environ.get('AD_PASS5')
    ldap_port = os.environ.get('LDAP_PORT')
    group = os.environ.get('AD_GROUP')

    # login with user5 to create a new environment
    get_authed_token(username=ldap_user5,
                     password=ldap_pass5)

    main_client = create_ad_client(username=ldap_main_user,
                                   password=ldap_main_pass)
    user = ADMIN_TOKEN['userIdentity']
    allowed_identities = []
    allowed_identities.append(user)

    group_identity = main_client.list_identity(name=group)[0]
    group_identity_dict = ast.literal_eval(str(group_identity))
    allowed_identities.append(group_identity_dict)

    # Enable new configuration
    config = load_config(access_mode='restricted')
    config['enabled'] = True
    config['allowedIdentities'] = allowed_identities
    if ldap_port == 'True':
        access_key = ADMIN_AD_CLIENT._access_key
        secret_key = ADMIN_AD_CLIENT._secret_key
        auth_url = cattle_url()[:-7] + 'v1-auth/config'
        r = requests.post(auth_url, data=json.dumps(config),
                          auth=(access_key, secret_key))
        assert r.ok
    else:
        ADMIN_AD_CLIENT.create_ldapconfig(config)

    # Try to login with user2 and user3
    token2 = get_authed_token(username=ldap_user2,
                              password=ldap_pass2)
    try:
        get_authed_token(username=ldap_user3,
                         password=ldap_pass3)
    except AssertionError as e:
        assert '401' in str(e)

    token5 = get_authed_token(username=ldap_user5,
                              password=ldap_pass5)

    cookies = dict(token=token2['jwt'])
    good_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert good_auth.status_code == 200

    cookies = dict(token=token5['jwt'])
    good_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert good_auth.status_code == 200

    def fin():
        reconfigure_ad(ADMIN_AD_CLIENT,
                       os.environ.get('API_AUTH_AD_SEARCH_BASE'), '')
    request.addfinalizer(fin)
