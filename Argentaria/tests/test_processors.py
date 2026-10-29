import pytest

from services.operations import TransferProcessor
from services.transaction_processors import CashDepositProcessor, CashWithdrawalProcessor
from test_operations import bank


@pytest.mark.parametrize("processor", [CashDepositProcessor, CashWithdrawalProcessor, TransferProcessor])
@pytest.mark.parametrize("value", [None, True, "not-numeric", "NaN", "Infinity", 0, -.01, "1.001"])
def test_processor_public_entrypoints_validate_before_mutation(bank, processor, value):
    _, session, repo, _, _ = bank
    account = session.get_account()
    before = account.get_balance()
    original = repo.data_file.read_bytes()
    args = [account, value, repo, "Fixture ATM", "ATM-1", "Self", "Test", "", "EUR", True]
    if processor is TransferProcessor:
        args.insert(1, repo.find_by_account_number("1000 2200 7788"))
        args.append("2026-10-29T12:00:00+00:00")
    with pytest.raises(ValueError):
        processor().process(*args)
    assert account.get_balance() == before
    assert repo.data_file.read_bytes() == original


@pytest.mark.parametrize("processor,amount", [(CashDepositProcessor, 5000.01), (CashWithdrawalProcessor, 1000.01), (TransferProcessor, 5000.01)])
def test_each_processor_enforces_its_single_operation_limit(bank, processor, amount):
    _, session, repo, _, _ = bank
    account = session.get_account()
    args = [account, amount, repo, "Fixture ATM", "ATM-1", "Self", "Test", "", "EUR", True]
    if processor is TransferProcessor:
        args.insert(1, repo.find_by_account_number("1000 2200 7788"))
        args.append("2026-10-29T12:00:00+00:00")
    with pytest.raises(ValueError, match="limited"):
        processor().process(*args)


@pytest.mark.parametrize("processor", [CashDepositProcessor, CashWithdrawalProcessor, TransferProcessor])
def test_processors_reject_inactive_card(bank, processor):
    _, session, repo, _, _ = bank
    account = session.get_account()
    account.card.status = "blocked"
    args = [account, 10, repo, "Fixture ATM", "ATM-1", "Self", "Test", "", "EUR", True]
    if processor is TransferProcessor:
        args.insert(1, repo.find_by_account_number("1000 2200 7788"))
        args.append("2026-10-29T12:00:00+00:00")
    with pytest.raises(ValueError, match="active"):
        processor().process(*args)


@pytest.mark.parametrize("processor,expected_balance,kind", [(CashDepositProcessor, 2460.75, "DEPOSIT"), (CashWithdrawalProcessor, 2440.75, "WITHDRAWAL")])
def test_cash_processor_standalone_persistence_contract(bank, processor, expected_balance, kind):
    _, session, repo, _, _ = bank
    result = processor().process(session.get_account(), 10, repo, "Fixture ATM", "ATM-1", "Self", "Test", "", "EUR", True)
    assert result.kind == kind and result.amount == 10
    assert result.balance_after == expected_balance
    reloaded = repo.find_by_card("4556123412341234")
    assert reloaded.get_balance() == expected_balance
    assert reloaded.get_transactions()[0].transaction_id == result.transaction_id


def test_withdrawal_and_transfer_processors_reject_insufficient_funds(bank):
    _, session, repo, _, _ = bank
    account = session.get_account()
    account._balance = -300
    with pytest.raises(ValueError, match="Insufficient"):
        CashWithdrawalProcessor().process(account, 1, repo, "ATM", "1", "Self", "Test", "", "EUR", True)
    destination = repo.find_by_account_number("1000 2200 7788")
    with pytest.raises(ValueError, match="Insufficient"):
        TransferProcessor().process(account, destination, 1, repo, "ATM", "1", "Self", "Test", "", "EUR", True, "2026-10-29T12:00:00+00:00")


def test_transfer_processor_generates_default_descriptions_and_linked_records(bank):
    _, session, repo, _, _ = bank
    account = session.get_account()
    destination = repo.find_by_account_number("1000 2200 7788")
    result = TransferProcessor().process(account, destination, 10, repo, "ATM", "1", "Self", "Test", "", "EUR", True, "2026-10-29T12:00:00+00:00")
    assert result.note == "Transfer to 1000 2200 7788"
    assert destination.get_transactions()[0].note == "Transfer from 1000 2200 3344"
    assert destination.get_transactions()[0].transaction_id == result.transaction_id
