from abc import ABC, abstractmethod

class BaseExchange(ABC):
    
    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass
