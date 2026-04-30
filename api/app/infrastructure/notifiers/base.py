from abc import ABC, abstractmethod
from typing import List, Optional

class BaseNotifier(ABC):
    """
    Abstract Base Class for all notification channels.
    """
    
    @abstractmethod
    async def send(self, message: str, **kwargs) -> bool:
        """
        Sends a message through the channel.
        :param message: Content of the message
        :param kwargs: Channel-specific options (e.g., parse_mode, images)
        :return: True if successful, False otherwise.
        """
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """
        Checks if the channel is configured and reachable.
        """
        pass
