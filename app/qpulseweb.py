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
        url = 'http://10.182.155.37/QPulseWeb.asmx?WSDL'
        client = Client(url, cache=NoCache())
        print client
        return client

    def get_doc_by_id(self, username, password, docNumber):
        """
        Gets doc name by qpulse id using the starlims web service

        :param username:
        :param password:
        :param docNumber:
        :return:
        """
        params = {"username":username, "password":password, "docNumber":docNumber }
        client = self._get_client()
        response = client.service.GetDocByID(**params)
        print response
        return response