import urllib.error
from suds.client import Client
from suds.sudsobject import asdict
from suds.cache import NoCache

class QPulseWeb:
    def __init__(self):
        pass

    def _get_client(self):
        """
        contacts the webservice and gets a client with suds

        :return: client object
        """
        url = 'https://bioinfoweb.sch.nhs.uk/QPulseWeb.asmx?WSDL'
        client = Client(url, cache=NoCache())
        return client


    def get_doc_by_id(self, username, password, docNumber):
        """
        Gets doc name by qpulse id using the starlims web service

        :param username:
        :param password:
        :param docNumber:
        :return:
        """
        try:
            params = {"username":username, "password":password, "docNumber":docNumber }
            client = self._get_client()
            response = client.service.GetDocByID(**params)
            return response
        except urllib.error.URLError:
            return "Error connecting to Q-Pulse"

    ### Looks as though the API is only querying the active register?
    # def check_doc_active(self, username, password, docNumber):
    #     """
    #     Checks a document is active via bioinfoweb
    #     """
    #     params = {"username":username, "password":password, "docNumber":docNumber}
    #     client = self._get_client()
    #     response = client.service.IsDocActive(**params)
    #     return response
