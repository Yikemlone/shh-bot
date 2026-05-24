from services.music.queue import QueueManagerService


def test_add_to_queue():
    q = QueueManagerService()
    q.add_to_queue({"URL": "song1", "name": "A", "song": "Song A"})
    q.add_to_queue({"URL": "song2", "name": "B", "song": "Song B"})
    assert len(q.get_song_queue()) == 2


def test_set_and_get_current_song():
    q = QueueManagerService()
    song = {"URL": "url", "name": "Artist", "song": "Title"}
    q.set_current_song(song)
    assert q.get_current_song() == song


def test_update_queue_pops_next():
    q = QueueManagerService()
    q.set_current_song({"URL": "old", "name": "A", "song": "Old"})
    q.add_to_queue({"URL": "next", "name": "B", "song": "Next"})
    q.update_queue()
    assert q.get_current_song()["song"] == "Next"
    assert len(q.get_song_queue()) == 0


def test_update_queue_looping_readds():
    q = QueueManagerService()
    q.toggleLooping()
    q.set_current_song({"URL": "url", "name": "A", "song": "Song"})
    q.update_queue()
    assert q.get_current_song()["song"] == "Song"


def test_update_queue_looping_multiple_keeps_order():
    q = QueueManagerService()
    q.toggleLooping()
    q.set_current_song({"URL": "a", "name": "A", "song": "Song A"})
    q.add_to_queue({"URL": "b", "name": "B", "song": "Song B"})
    q.update_queue()
    assert q.get_current_song()["song"] == "Song B"
    assert q.get_song_queue() == [{"URL": "a", "name": "A", "song": "Song A"}]


def test_update_queue_empty_clears_current():
    q = QueueManagerService()
    q.set_current_song({"URL": "url", "name": "A", "song": "Song"})
    q.update_queue()
    assert q.get_current_song() == {}


def test_reset_queue_clears_everything():
    q = QueueManagerService()
    q.set_current_song({"URL": "url", "name": "A", "song": "Song"})
    q.add_to_queue({"URL": "url2", "name": "B", "song": "Song2"})
    q.reset_queue()
    assert q.get_current_song() == {}
    assert len(q.get_song_queue()) == 0


def test_is_there_playable_songs():
    q = QueueManagerService()
    assert not q.isTherePlayableSongs()
    q.set_current_song({"URL": "url", "name": "A", "song": "Song"})
    assert q.isTherePlayableSongs()


def test_toggle_looping():
    q = QueueManagerService()
    assert not q.isLooping()
    q.toggleLooping()
    assert q.isLooping()
    q.toggleLooping()
    assert not q.isLooping()
