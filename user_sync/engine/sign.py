import logging
from collections import defaultdict

import six

from user_sync import error, identity_type
from user_sync.config.common import DictConfig, ConfigFileLoader
from user_sync.connector.connector_sign import SignConnector
from user_sync.engine.umapi import AdobeGroup
from user_sync.error import AssertionException
from user_sync.helper import normalize_string


class SignSyncEngine:
    default_options = {
        'create_users': False,
        'deactivate_users': False,
        'extended_attributes': None,
        'identity_source': {
            'type': 'ldap',
            'connector': 'connector-ldap.yml'
        },
        'invocation_defaults': {
            'users': 'mapped'
        },
        'sign_orgs': [
            {'primary': 'connector-sign.yml'}
        ],
        'user_sync': {
            'create_users': False,
            'deactivate_users': False,
            'sign_only_limit': 100
        }
    }

    name = 'sign_sync'
    encoding = 'utf-8'
    DEFAULT_GROUP_NAME = 'default group'

    def __init__(self, caller_options):
        """
        Initialize the Sign Sync Engine
        :param caller_options:
        :return:
        """
        super().__init__()
        options = dict(self.default_options)
        options.update(caller_options)
        self.options = options
        self.logger = logging.getLogger(self.name)
        self.test_mode = options.get('test_mode')
        sync_config = DictConfig('<%s configuration>' %
                                 self.name, caller_options)
        self.directory_user_by_user_key = {}
        sign_orgs = sync_config.get_dict('sign_orgs')
        self.config_loader = ConfigFileLoader(self.encoding, {}, {})
        self.connectors = {}
        # Each of the Sign orgs is captured in a dict with the org name as key
        # and org specific parameter embedded in Sign Connector as value
        for org in sign_orgs:
            self.connectors[org] = SignConnector(
                self.config_loader.load_root_config(sign_orgs[org]), org)

        self.action_summary = {}
        self.sign_users_by_org = {}
        self.total_sign_user_count = 0
        self.sign_users_created = set()
        self.sign_users_deactivated = set()
        self.sign_admins_matched = set()
        self.sign_users_matched_groups = set()
        self.sign_users_group_updates = set()
        self.sign_users_role_updates = set()
        self.sign_users_matched_no_updates = set()
        self.directory_users_excluded = set()
        self.sign_only_users_by_email = {}


    def run(self, directory_groups, directory_connector):
        """
        Run the Sign sync
        :param directory_groups:
        :param directory_connector:
        :return:
        """
        if self.test_mode:
            self.logger.info("Sign Sync disabled in test mode")
            return
        self.read_desired_user_groups(directory_groups, directory_connector)

        for org_name, sign_connector in self.connectors.items():
            # Create any new Sign groups
            org_directory_groups = self._groupify(
                org_name, directory_groups.values())
            org_sign_groups = [x.lower() for x in sign_connector.sign_groups()]
            for directory_group in org_directory_groups:
                if (directory_group.lower() not in org_sign_groups):
                    self.logger.info(
                        "Creating new Sign group: {}".format(directory_group))
                    sign_connector.create_group(directory_group)
            # Update user details or insert new user        
            self.update_sign_users(
                    self.directory_user_by_user_key, sign_connector, org_name)
            if self.options['deactivate_users'] is True and sign_connector.neptune_console is True:
                self.deactivate_sign_users(self.directory_user_by_user_key, sign_connector, org_name)
        self.log_action_summary()

    def log_action_summary(self):

        self.action_summary = {
            'Number of directory users read': len(self.directory_user_by_user_key),
            'Number of directory selected for input': len(self.directory_user_by_user_key) - len(self.directory_users_excluded),
            'Number of directory users excluded': len(self.directory_users_excluded),
            'Number of Sign users read': self.total_sign_user_count,
            'Number of Sign users not in directory (sign-only)': len(self.sign_only_users_by_email),
            'Number of Sign users updated': len(self.sign_users_group_updates | self.sign_users_role_updates),
            'Number of users with matched groups unchanged': len(self.sign_users_matched_groups),
            'Number of users with admin roles unchanged': len(self.sign_admins_matched),
            'Number of users with groups updated': len(self.sign_users_group_updates),
            'Number of users admin roles updated': len(self.sign_users_role_updates),
            'Number of users matched with no updates': len(self.sign_users_matched_no_updates),
        }

        if self.options['create_users']:
            self.action_summary['Number of Sign users created'] = len(self.sign_users_created)
        if self.options['deactivate_users']:
            self.action_summary['Number of Sign users deactivated'] = len(self.sign_users_deactivated)

        pad = max(len(k) for k in self.action_summary)
        header = '------- Action Summary -------'
        self.logger.info('---------------------------' + header + '---------------------------')
        for description, count in self.action_summary.items():
            self.logger.info('  {}: {}'.format(description.rjust(pad, ' '), count))

    def update_sign_users(self, directory_users, sign_connector, org_name):
        """
        Updates user details or inserts new user
        :param directory_groups:
        :param sign_connector:
        :param org_name:
        :return:
        """
        # Fetch the list of active Sign users
        sign_users = sign_connector.get_users()
        self.total_sign_user_count = len(sign_users)
        self.sign_users_by_org[org_name] = sign_users
        for _, directory_user in directory_users.items():
            sign_user = sign_users.get(directory_user['email'])
            if not self.should_sync(directory_user, org_name):
                continue

            assignment_group = self.retrieve_assignment_group(directory_user)

            if assignment_group is None:
                assignment_group = self.DEFAULT_GROUP_NAME

            group_id = sign_connector.get_group(assignment_group.lower())
            admin_roles = self.retrieve_admin_role(directory_user)
            user_roles = self.resolve_new_roles(
                directory_user, sign_user, admin_roles)
            if sign_user is None:
                # Insert new user if flag is enabled and if Neptune Console
                if self.options['create_users'] is True and sign_connector.neptune_console is True:
                    self.insert_new_users(
                        sign_connector, directory_user, user_roles, group_id, assignment_group)
                else:
                    self.logger.info("User {} not present in Sign and will be skipped.".format(directory_user['email']))
                    self.directory_users_excluded.add(directory_user['email'])
                    continue
            else:
                # Update existing users
                self.update_existing_users(
                    sign_connector, sign_user, directory_user, group_id, user_roles, assignment_group)
        self.resolve_sign_only_users(directory_users, sign_users)

    def resolve_sign_only_users(self, directory_users, sign_users):

        for user, data in sign_users.items():
            if user not in directory_users:
                self.sign_only_users_by_email[user] = data


    @staticmethod
    def roles_match(resolved_roles, sign_roles):
        """
        Checks if the existing user role in Sign Console is same as in configuration
        :param resolved_roles:
        :param sign_roles:
        :return:
        """
        if isinstance(sign_roles, str):
            sign_roles = [sign_roles]
        return sorted(resolved_roles) == sorted(sign_roles)

    @staticmethod
    def resolve_new_roles(directory_user, sign_user, user_roles):
        """
        Updates the user role (if applicable) as specified in the configuration
        :param resolved_roles:
        :param sign_roles:
        :param user_roles:
        :return:
        """
        if (user_roles is None or all(x is None for x in user_roles)):
            if sign_user is None:
                return ['NORMAL_USER']
            else:
                return sign_user['roles']
        else:
           return user_roles

    def should_sync(self, directory_user, org_name):
        """
        Initial gatekeeping to determine if user is candidate for Sign sync
        Any checks that don't depend on the Sign record go here
        Sign record must be defined for user, and user must belong to at least one entitlement group
        and user must be accepted identity type
        :param umapi_user:
        :param org_name:
        :return:
        """
        return directory_user['sign_groups']['groups'][0].umapi_name == org_name

    def retrieve_assignment_group(self, directory_user):
        return directory_user['sign_groups']['groups'][0].group_name

    def retrieve_admin_role(self, directory_user):
        return directory_user['sign_groups']['roles']

    @staticmethod
    def _groupify(org_name, groups):
        """
        Extracts the Sign Group name from the configuration for an org
        :param org_name:
        :param groups:
        :return:
        """
        processed_groups = []
        for group_dict in groups:
            for group in group_dict['groups']:
                group_name = group.group_name
                if (org_name == group.umapi_name):
                    processed_groups.append(group_name)
        return processed_groups

    def read_desired_user_groups(self, mappings, directory_connector):
        """
        Reads and loads the users and group information from the identity source
        :param mappings:
        :param directory_connector:
        :return:
        """
        self.logger.debug('Building work list...')

        options = self.options
        directory_group_filter = options['users']
        if directory_group_filter is not None:
            directory_group_filter = set(directory_group_filter)
        extended_attributes = options.get('extended_attributes')

        directory_user_by_user_key = self.directory_user_by_user_key

        directory_groups = set(six.iterkeys(mappings))
        if directory_group_filter is not None:
            directory_groups.update(directory_group_filter)
        directory_users = directory_connector.load_users_and_groups(groups=directory_groups,
                                                                    extended_attributes=extended_attributes,
                                                                    all_users=directory_group_filter is None)

        for directory_user in directory_users:
            user_key = self.get_directory_user_key(directory_user)
            if not user_key:
                self.logger.warning(
                    "Ignoring directory user with empty user key: %s", directory_user)
                continue
            sign_groups = self.extract_mapped_group(
                directory_user['groups'], mappings)
            directory_user['sign_groups'] = sign_groups
            directory_user_by_user_key[user_key] = directory_user

    def get_directory_user_key(self, directory_user):
        """
        :type directory_user: dict
        """
        email = directory_user.get('email')
        if email:
            return six.text_type(email)
        return None

    def get_user_key(self, id_type, username, domain, email=None):
        """
        Construct the user key for a directory or adobe user.
        The user key is the stringification of the tuple (id_type, username, domain)
        but the domain part is left empty if the username is an email address.
        If the parameters are invalid, None is returned.
        :param username: (required) username of the user, can be his email
        :param domain: (optional) domain of the user
        :param email: (optional) email of the user
        :param id_type: (required) id_type of the user
        :return: string "id_type,username,domain" (or None)
        :rtype: str
        """
        id_type = identity_type.parse_identity_type(id_type)
        email = normalize_string(email) if email else None
        username = normalize_string(username) or email
        domain = normalize_string(domain)

        if not id_type:
            return None
        if not username:
            return None
        if username.find('@') >= 0:
            domain = ""
        elif not domain:
            return None
        return six.text_type(id_type) + u',' + six.text_type(username) + u',' + six.text_type(domain)

    def get_identity_type_from_directory_user(self, directory_user):
        identity_type = directory_user.get('identity_type')
        if identity_type is None:
            identity_type = self.options['new_account_type']
            self.logger.warning('Found user with no identity type, using %s: %s', identity_type, directory_user)
        return identity_type

    def extract_mapped_group(self, directory_user_group, group_mapping):
        for directory_group, sign_group_mapping in group_mapping.items():
            if (directory_user_group[0] == directory_group):
                return sign_group_mapping

    def update_existing_users(self, sign_connector, sign_user, directory_user, group_id, user_roles, assignment_group):
        """
        Constructs the data for update and invokes the connector to update the user if applicable
        :param sign_connector:
        :param sign_user:
        :param directory_user:
        :param group_id:
        :param user_roles:
        :param assignment_group:
        :return:
        """
        update_data = {
            "email": sign_user['email'],
            "firstName": sign_user['firstName'],
            "groupId": group_id,
            "lastName": sign_user['lastName'],
            "roles": user_roles,
        }
        groups_match = sign_user['group'].lower() == assignment_group.lower()
        roles_match = self.roles_match(user_roles, sign_user['roles'])

        if not roles_match:
            self.sign_users_role_updates.add(sign_user['email'])
        elif user_roles != ['NORMAL_USER']:
            self.sign_admins_matched.add(sign_user['email'])
        if not groups_match:
            self.sign_users_group_updates.add(sign_user['email'])
        else:
            self.sign_users_matched_groups.add(sign_user['email'])

        if groups_match and roles_match:
            self.logger.debug(
                "skipping Sign update for '{}' -- no updates needed".format(directory_user['email']))
            self.sign_users_matched_no_updates.add(sign_user['email'])
            return
        try:
            sign_connector.update_user(sign_user['userId'], update_data)
            self.logger.info("Updated Sign user '{}', Group ({}): '{}', Roles ({}): {}".format(
                directory_user['email'], 'unchanged' if groups_match else 'new', assignment_group,
                'unchanged' if roles_match else 'new', update_data['roles']))
        except AssertionError as e:
            self.logger.error("Error updating user {}".format(e))

    def insert_new_users(self, sign_connector, directory_user, user_roles, group_id, assignment_group):
        """
        Constructs the data for insertion and inserts new user in the Sign Console
        :param sign_connector:
        :param directory_user:
        :param user_roles:
        :param group_id:
        :param assignment_group:
        :return:
        """
        insert_data = {
            "email": directory_user['email'],
            "firstName": directory_user['firstname'],
            "groupId": group_id,
            "lastName": directory_user['lastname'],
            "roles": user_roles,
        }
        try:
            sign_connector.insert_user(insert_data)
            self.sign_users_created.add(directory_user['email'])
            self.logger.info("Inserted Sign user '{}', Group: '{}', Roles: {}".format(
                directory_user['email'], assignment_group, insert_data['roles']))
        except AssertionException as e:
            self.logger.error(format(e))
        return
        
    def deactivate_sign_users(self, directory_users, sign_connector, org_name):
        """
        Searches users to deactivate in the Sign Netpune console
        :param sign_connector:
        :param sign_user:
        :return:
        """
        #sign_users = self.sign_users_by_org[org_name]
        #if sign_users is None:
        sign_users = sign_connector.get_users()
        director_users_emails = []
        director_users_emails = list(map(lambda directory_user:directory_user['email'].lower(), directory_users.values()))
        for _, sign_user in sign_users.items():
            if sign_user['email'].lower() not in director_users_emails:
                try:
                    sign_connector.deactivate_user(sign_user['userId'])
                    self.sign_users_deactivated.add(sign_user['userId'])
                except AssertionException as e:
                    self.logger.error("Error deactivating user {}, {}".format(sign_user['email'], e))
                return
                