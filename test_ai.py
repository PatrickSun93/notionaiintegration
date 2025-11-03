from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    def test(self):
        pass

print("AIProvider defined successfully")