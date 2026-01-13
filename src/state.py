import threading

_pause_event = threading.Event()
_pause_event.set()
_stop_flag = False
_lock = threading.Lock()


def pause():
    _pause_event.clear()
    print("\n⏸ Paused")


def resume():
    _pause_event.set()
    print("\n⏵ Resumed")


def stop():
    global _stop_flag
    with _lock:
        _stop_flag = True
    _pause_event.set()
    print("\n⏹ Stopped")


def reset():
    global _stop_flag
    with _lock:
        _stop_flag = False
    _pause_event.set()


def is_stopped() -> bool:
    with _lock:
        return _stop_flag


def wait_if_paused() -> bool:
    _pause_event.wait()
    return not is_stopped()
