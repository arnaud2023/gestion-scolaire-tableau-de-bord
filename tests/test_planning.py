import unittest

from planning import has_time_conflict


class TimeConflictTests(unittest.TestCase):
    def setUp(self):
        self.session = {
            "id": 1,
            "jour": "Lundi",
            "heure_debut": "08:00",
            "heure_fin": "09:00",
            "classe_id": 1,
            "enseignant_id": 2,
            "salle_id": 3,
        }

    def test_overlapping_class_is_rejected(self):
        candidate = {**self.session, "id": None, "heure_debut": "08:30", "heure_fin": "09:30"}
        self.assertIn("classe", has_time_conflict(candidate, [self.session]))

    def test_adjacent_slots_are_allowed(self):
        candidate = {**self.session, "id": None, "heure_debut": "09:00", "heure_fin": "10:00"}
        self.assertIsNone(has_time_conflict(candidate, [self.session]))

    def test_other_day_is_allowed(self):
        candidate = {**self.session, "id": None, "jour": "Mardi"}
        self.assertIsNone(has_time_conflict(candidate, [self.session]))

    def test_invalid_duration_is_rejected(self):
        candidate = {**self.session, "heure_debut": "10:00", "heure_fin": "09:00"}
        self.assertIn("fin", has_time_conflict(candidate, []))


if __name__ == "__main__":
    unittest.main()
