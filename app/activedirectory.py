"""Access StarlIMS functionality via sdgs webservice.
"""
from suds.client import Client
from suds.sudsobject import asdict
from suds.cache import NoCache
import ssl

class UserAuthentication:
    def __init__(self):
        pass

    def _get_client(self):
        """
        contacts the webservice and gets a client with suds

        :return: client object
        """
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context

        url = 'https://bioinfoweb.sch.nhs.uk/UserAuthentication.asmx?WSDL'
        client = Client(url, cache=NoCache())
        return client

    def authenticate(self, username, password):
        """
        method to get the patients on a sequencer run

        :param run_id: hiseq folder name i.e. 150709_D00461_0040_AHTC7VADXX
        :return: list of dicts containing patients on the run
        """
        credentials = {"username": username,"password":password, "dbupdate":0}
        client = self._get_client()
        response = client.service.GetUserAuth(**credentials)
        return response

    def get_user_detail_from_username(self,username):
        """
        get user information from username

        :param username: active directory username
        :return: dictionary containing forename,surname and email
        """
        username = {"username": username}
        client = self._get_client()
        response = client.service.GetUserDetailFromUsername(**username)
        return response

    def get_username_from_user_detail(self, firstname,lastname):
        """
        get user information from username

        :param username: active directory username
        :return: dictionary containing forename,surname and email
        """
        username = {"firstName": firstname, "lastName": lastname}
        client = self._get_client()
        response = client.service.GetUserDetailFromFullName(**username)
        return response

