"""Offline capability checks; no desktop or recorder process is started."""
import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "evidence", Path(__file__).resolve().parents[1] / "evidence-driven-testing/scripts/evidence.py")
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


class WaylandTests(unittest.TestCase):
    def test_desktop_name_never_substitutes_for_protocol_probe(self):
        with patch.object(evidence.shutil, "which", return_value=None), patch.dict(
                evidence.os.environ, {"XDG_CURRENT_DESKTOP": "sway", "WAYLAND_DISPLAY": "wayland-0"}):
            available, reason = evidence.wayland_capture_support()
        self.assertFalse(available)
        self.assertIn("cannot confirm", reason)

    def test_successful_probe_requires_the_protocol(self):
        for output, expected in (("wl_output", False), (evidence.WLR_SCREENCOPY_PROTOCOL, True)):
            with self.subTest(output=output), patch.object(evidence.shutil, "which", return_value="probe"), patch.object(
                    evidence.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=output)):
                self.assertEqual(evidence.wayland_capture_support()[0], expected)

    def test_failed_probe_output_is_not_capability_evidence(self):
        with patch.object(evidence.shutil, "which", return_value="probe"), patch.object(
                evidence.subprocess, "run", return_value=SimpleNamespace(
                    returncode=1, stdout=evidence.WLR_SCREENCOPY_PROTOCOL)):
            self.assertFalse(evidence.wayland_capture_support()[0])

    def test_failed_first_probe_can_recover_with_second(self):
        for failure in (OSError("unavailable"), subprocess.TimeoutExpired("probe", 5)):
            with self.subTest(failure=failure), patch.object(evidence.shutil, "which", return_value="probe"), patch.object(
                    evidence.subprocess, "run", side_effect=[failure, SimpleNamespace(
                        returncode=0, stdout=evidence.WLR_SCREENCOPY_PROTOCOL)]):
                self.assertTrue(evidence.wayland_capture_support()[0])

    def test_explicit_source_does_not_claim_automatic_support(self):
        self.assertEqual(evidence.resolve_source("wayland"), "wayland")


if __name__ == "__main__":
    unittest.main()
