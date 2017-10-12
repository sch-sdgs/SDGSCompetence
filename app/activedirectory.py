"""Access StarlIMS functionality via sdgs webservice.
"""
from suds.client import Client
from suds.sudsobject import asdict

class UserAuthentication:
    def __init__(self):
        pass

    def _get_client(self):
        """
        contacts the webservice and gets a client with suds

        :return: client object
        """
        url = "http://10.182.155.37/UserAuthentication.asmx?WSDL"
        client = Client(url)
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
