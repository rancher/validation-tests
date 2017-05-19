from common_fixtures import *  # NOQA
from requests.auth import AuthBase


if_ldap = pytest.mark.skipif(not os.environ.get('API_AUTH_LDAP_SERVER'),
                             reason='API_AUTH_LDAP_SERVER is not set')


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


def load_config():
    config = {
        "accessMode": "unrestricted",
        'domain': os.environ.get('API_AUTH_LDAP_DOMAIN', "dc=rancher,dc=io"),
        'groupNameField': os.environ.get('API_AUTH_LDAP_GROUP_NAME_FIELD',
                                         'name'),
        'groupObjectClass': os.environ.get('API_AUTH_LDAP_GROUP_OBJECT_CLASS',
                                           'group'),
        'groupSearchField': os.environ.get('API_AUTH_LDAP_GROUP_SEARCH_FIELD',
                                           'sAMAccountName'),
        'loginDomain': os.environ.get('API_AUTH_LDAP_LOGIN_NAME', 'rancher'),
        'port': os.environ.get('API_AUTH_LDAP_PORT', 389),
        'enabled': False,
        'server': os.environ.get('API_AUTH_LDAP_SERVER', 'ad.rancher.io'),
        'serviceAccountPassword': os.environ.get('API_AUTH_LDAP_'
                                                 'SERVICE_ACCOUNT_PASSWORD',
                                                 'Password1'),
        'serviceAccountUsername': os.environ.get('API_AUTH_LDAP_'
                                                 'SERVICE_ACCOUNT_USERNAME',
                                                 'cattle'),
        'tls': False,
        'userDisabledBitMask': os.environ.get('API_AUTH_LDAP_'
                                              'USER_DISABLED_BIT_MASK',
                                              '2'),
        'userEnabledAttribute': os.environ.get('API_AUTH_LDAP_'
                                               'USER_ENABLED_ATTRIBUTE',
                                               'userAccountControl'),
        'userLoginField': os.environ.get('API_AUTH_LDAP_USER_LOGIN_FIELD',
                                         'sAMAccountName'),
        'userNameField': os.environ.get('API_AUTH_LDAP_'
                                        'USER_NAME_FIELD', 'name'),
        'userObjectClass': os.environ.get('API_AUTH_LDAP_USER_OBJECT_CLASS',
                                          'person'),
        'userSearchField': os.environ.get('API_AUTH_LDAP_USER_SEARCH_FIELD',
                                          'name')
    }
    return config


@pytest.fixture(scope='module', autouse=True)
def ldap_config(admin_client, request):
    config = load_config()
    admin_client.create_ldapconfig(config)
    service_account_dn = os.getenv('API_AUTH_LDAP_SERVICE_ACCOUNT_DN',
                                   "cn=Cattle,"
                                   "ou=Rancher Labs,dc=rancher,dc=io")
    x = admin_client.by_id('identity', 'ldap_user:' + service_account_dn)
    assert x.login == config['serviceAccountUsername']


@if_ldap
def test_ldap_search_get_user(admin_client):
    search_user = os.getenv('LDAP_USER1', 'devUserA')
    search_user_name = os.getenv('LDAP_USER_NAME', 'Dev A. User')
    user = admin_client.list_identity(name=search_user_name)[0]
    assert user.name == search_user_name
    assert user.login == search_user
    user_copy = admin_client.by_id('identity', user.id)
    assert user.name == user_copy.name
    assert user.id == user_copy.id
    assert user.login == user_copy.login
    assert user.profilePicture == user_copy.profilePicture
    assert user.profileUrl == user_copy.profileUrl


@if_ldap
def test_ldap_search_get_group(admin_client):
    search_group = os.getenv('LDAP_GROUP', 'qualityAssurance')
    group = admin_client.list_identity(name=search_group)[0]
    group_copy = admin_client.by_id('identity', group.id)
    assert group.name == group_copy.name
    assert group.id == group_copy.id
    assert group.login == group_copy.login
    assert group.profilePicture == group_copy.profilePicture
    assert group.profileUrl == group_copy.profileUrl


def ldap_client(username, password):
    token = requests.post(base_url() + 'token', {
        'code': username + ':' + password,
        'authProvider': 'ldapconfig'
    })
    token = token.json()
    assert token['type'] != 'error'
    token = token['jwt']
    ldap_client = from_env(url=cattle_url())
    ldap_client.valid()
    ldap_client._auth = LdapAuth(token)
    identities = ldap_client.list_identity()
    assert len(identities) > 0
    non_rancher = False
    for identity in identities:
        if (identity.externalIdType == 'ldap_user'):
            non_rancher = True
    assert non_rancher
    return ldap_client


@if_ldap
def test_ldap_login(admin_client, cattle_url):
    username = os.getenv('LDAP_USER1', 'devUserA')
    password = os.getenv('LDAP_USER1_PASSWORD', 'Password1')
    ldap_client(username, password)


@if_ldap
def test_ldap_incorrect_login():
    username = os.getenv('LDAP_USER1', 'devUserA')
    token = requests.post(base_url() + 'token',
                          {
                              'code': username + ':' + random_str(),
                              'authProvider': 'ldapconfig'
    })
    assert token.status_code == 401
    token = token.json()
    assert token['type'] == 'error'
    assert token['status'] == 401


@if_ldap
def test_ldap_unauthorized_login():
    username = os.environ.get('API_AUTH_LDAP_'
                              'SERVICE_ACCOUNT_PASSWORD',
                              'Password1')
    password = os.environ.get('API_AUTH_LDAP_'
                              'SERVICE_ACCOUNT_USERNAME',
                              'cattle')
    token = requests.post(base_url() + 'token',
                          {
                              'code': username + ':' + password,
                              'authProvider': 'ldapconfig'
    })
    assert token.status_code == 401
    token = token.json()
    assert token['type'] == 'error'
    assert token['status'] == 401


@if_ldap
def test_ldap_project_members():
    username = os.getenv('LDAP_USER1', 'devUserA')
    password = os.getenv('LDAP_USER1_PASSWORD', 'Password1')
    user1_client = ldap_client(username, password)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            user1_identity = obj
            break
    username = os.getenv('LDAP_USER2', 'devUserB')
    password = os.getenv('LDAP_USER2_PASSWORD', 'Password1')
    user2_client = ldap_client(username, password)
    user2_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            user2_identity = obj
            break
    group = os.getenv('LDAP_GROUP', 'qualityAssurance')
    group = user1_client.list_identity(name=group)[0]
    project = user1_client.create_project(members=[
        idToMember(user1_identity, 'owner'),
        idToMember(user2_identity, 'member')
    ])
    project = user1_client.wait_success(project)
    user2_client.by_id('project', project.id)
    project.setmembers(members=[
        idToMember(group, 'owner')
    ])
    project = user2_client.by_id('project', project.id)
    user2_client.delete(project)


def idToMember(identity, role):
    return {
        'externalId': identity.externalId,
        'externalIdType': identity.externalIdType,
        'role': role
    }


@if_ldap
def test_ldap_project_create():
    username = os.getenv('LDAP_USER1', 'devUserA')
    password = os.getenv('LDAP_USER1_password', 'Password1')
    user1_client = ldap_client(username, password)
    identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'ldap_user':
            identity = obj
            break
    members = [idToMember(identity, 'owner')]
    project = user1_client.create_project(members=members)
    project = user1_client.wait_success(project)
    assert project is not None
    user1_client.delete(project)
