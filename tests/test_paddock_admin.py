"""Tests for deterministic rename preparation, confirmation, and audit writes."""

from __future__ import annotations

import unittest
from unittest.mock import patch
import asyncio

from app.app import AskRequest, _pending_renames, ask
from app.paddock_admin import RenameProposal, RenameRejected, confirm_rename, prepare_rename


class PaddockAdminTests(unittest.TestCase):
    @patch("app.paddock_admin.fetch_one")
    def test_prepare_rename_resolves_identity_and_rejects_duplicates(self, fetch_one) -> None:
        fetch_one.side_effect = [{"id": 7, "name": "Paddock A"}, None]
        proposal = prepare_rename("Paddock A", "North Flat")
        self.assertEqual(proposal, RenameProposal(7, "Paddock A", "North Flat"))
        fetch_one.side_effect = [{"id": 7, "name": "Paddock A"}, {"id": 8}]
        with self.assertRaises(RenameRejected):
            prepare_rename("Paddock A", "North Flat")

    @patch("app.paddock_admin.execute")
    @patch("app.paddock_admin.fetch_one")
    def test_confirm_rename_updates_display_name_and_writes_audit(self, fetch_one, execute) -> None:
        fetch_one.side_effect = [{"id": 7, "name": "Paddock A"}, None]
        proposal = confirm_rename(RenameProposal(7, "Paddock A", "North Flat"))
        self.assertEqual(proposal.new_name, "North Flat")
        self.assertEqual(execute.call_count, 2)
        self.assertIn("UPDATE paddocks", execute.call_args_list[0].args[0])
        self.assertIn("paddock_admin_audit", execute.call_args_list[1].args[0])

    @patch("app.app.confirm_rename")
    @patch("app.app.prepare_rename")
    def test_natural_language_rename_requires_confirmation(self, prepare, confirm) -> None:
        _pending_renames.clear()
        proposal = RenameProposal(7, "Paddock A", "North Flat")
        prepare.return_value = proposal
        confirm.return_value = proposal
        requested = asyncio.run(ask(AskRequest(question="Rename Paddock A to North Flat")))
        self.assertEqual(requested.intent, "rename-request")
        self.assertIsNotNone(requested.confirmation_id)
        self.assertIn("Reply", requested.answer)
        completed = asyncio.run(ask(AskRequest(question="confirm", confirmation_id=requested.confirmation_id)))
        self.assertEqual(completed.intent, "rename-confirmation")
        self.assertIn('Renamed "Paddock A" to "North Flat".', completed.answer)
        confirm.assert_called_once_with(proposal)


if __name__ == "__main__":
    unittest.main()
