import unittest
import threading
import time
from unittest.mock import patch
from io import StringIO

from src import state


class TestStateManagement(unittest.TestCase):

    def setUp(self):
        state.reset()

    def tearDown(self):
        state.reset()

    def test_initial_state_not_stopped(self):
        self.assertFalse(state.is_stopped())

    def test_stop_sets_flag(self):
        with patch('sys.stdout', new=StringIO()):
            state.stop()
        self.assertTrue(state.is_stopped())

    def test_reset_clears_stop_flag(self):
        with patch('sys.stdout', new=StringIO()):
            state.stop()
        self.assertTrue(state.is_stopped())
        state.reset()
        self.assertFalse(state.is_stopped())

    def test_wait_if_paused_returns_true_when_not_stopped(self):

        result = state.wait_if_paused()
        self.assertTrue(result)

    def test_wait_if_paused_returns_false_when_stopped(self):

        with patch('sys.stdout', new=StringIO()):
            state.stop()
        result = state.wait_if_paused()
        self.assertFalse(result)

    def test_pause_blocks_wait_if_paused(self):

        result_holder = {"unblocked": False, "result": None}

        def waiter():
            result_holder["result"] = state.wait_if_paused()
            result_holder["unblocked"] = True

        with patch('sys.stdout', new=StringIO()):
            state.pause()

        thread = threading.Thread(target=waiter)
        thread.start()

        time.sleep(0.1)
        self.assertFalse(result_holder["unblocked"])

        with patch('sys.stdout', new=StringIO()):
            state.resume()
        thread.join(timeout=1)

        self.assertTrue(result_holder["unblocked"])
        self.assertTrue(result_holder["result"])


class TestStateThreadSafety(unittest.TestCase):

    def setUp(self):
        state.reset()

    def tearDown(self):
        state.reset()

    def test_concurrent_stop_checks(self):

        results = []

        def check_stop():
            for _ in range(100):
                results.append(state.is_stopped())

        threads = [threading.Thread(target=check_stop) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 500)
        self.assertTrue(all(r is False for r in results))

    def test_stop_during_concurrent_checks(self):

        check_count = {"before_stop": 0, "after_stop": 0}
        stop_event = threading.Event()

        def checker():
            while not stop_event.is_set():
                if state.is_stopped():
                    check_count["after_stop"] += 1
                else:
                    check_count["before_stop"] += 1
                time.sleep(0.001)

        threads = [threading.Thread(target=checker) for _ in range(3)]
        for t in threads:
            t.start()

        time.sleep(0.05)
        with patch('sys.stdout', new=StringIO()):
            state.stop()
        time.sleep(0.05)

        stop_event.set()
        for t in threads:
            t.join()

        self.assertGreater(check_count["before_stop"], 0)
        self.assertGreater(check_count["after_stop"], 0)


if __name__ == "__main__":
    unittest.main()
