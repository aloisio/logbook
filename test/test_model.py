from model import Logbook


class TestLogbook:
    def test_valid_if_its_days_are_valid(self, tmp_path):
        Logbook(tmp_path)
