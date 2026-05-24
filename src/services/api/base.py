from abc import ABC, abstractmethod

class APIConnection(ABC):

    @staticmethod
    @abstractmethod
    def get_data(data):
        """This will be the main fucntion all API classes will use to call to interact with APIs."""
        pass
