from util.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

class QueueManagerService():

    def __init__(self):
        self.song_queue = []
        self.current_song = {}
        self.looping = False


    def get_song_queue(self) -> list[dict]:
        """Returns the song queue."""
        return self.song_queue

    def get_current_song(self) -> dict:
        """"Returns the current song in the queue."""
        return self.current_song
    
    def set_current_song(self, song : dict) -> None:
        """Sets the current song in the queue."""
        self.current_song = song

    def isLooping(self) -> bool:
        """Returns whether or not the queue is looping."""
        return self.looping
    
    def toggleLooping(self) -> None:
        """Toggles the looping state of the queue."""
        self.looping = not self.looping

    def add_to_queue(self, song_details : dict):
        """Adds a song to the end of the queue."""
        self.song_queue.append(song_details)

    def reset_queue(self) -> None:
        """Will reset the queue to an empty state."""
        self.song_queue = []
        self.current_song = {}

    def isTherePlayableSongs(self) -> bool:
        """Will check if there are any playable songs. If so, it will return True."""
        return len(self.get_song_queue()) > 0 or self.get_current_song()

    def update_queue(self) -> None:
        """Will update the current song and the queue list."""
        logger.info("Updating the current song and the queue list.")

        if self.looping:
            self.song_queue.append(self.current_song) 
        
        if len(self.song_queue) == 0:
            logger.info(f"No more songs in queue.")
            self.current_song = {}
            return

        self.set_current_song(self.song_queue[0])
        self.song_queue.pop(0)
