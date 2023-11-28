from pathlib import Path

import pytest

from chksum import (
    FileRenamer,
    QuarterSha256Base36Digester,
    Checksum,
    CheckCommand,
    ChecksumRepository,
    Presenter,
    ChecksumCalculator,
    ProcessPoolChecksumCalculator,
)

EMPTY_FILE_CHECKSUM = "3gng7kheu33tg"


def test_file_renamer_has_checksum_locked_file(tmp_path, renamer):
    names = [
        "example.1acceleration.txt",
        "example.0intelligence.mp4.1acceleration.jpg",
        "example.0intelligence.mp4.1acceleration.2professional",
    ]
    for name in names:
        file = tmp_path / name
        file.touch()
        assert renamer.has_checksum(file)
        assert renamer.checksum(file).value == "1acceleration"


def test_file_renamer_has_checksum_unlocked_file(tmp_path, renamer):
    names = [
        "example.txt",
        "example.0intelligence.mp4.jpg",
        "example.0intelligence.mp4.1acceleration",
        ".1acceleration",
        ".foobar",
        "example",
        "1acceleration",
    ]
    for name in names:
        file = tmp_path / name
        file.touch()
        assert not renamer.has_checksum(file), name
        with pytest.raises(ValueError):
            renamer.checksum(file)


def test_file_renamer_delete_locked_file(tmp_path, renamer):
    names = ["example.1acceleration.txt", f"example.{EMPTY_FILE_CHECKSUM}.txt"]
    for name in names:
        original_file = tmp_path / name
        original_file.touch()
        assert renamer.has_checksum(original_file)
        original_checksum = renamer.checksum(original_file)
        assert str(original_checksum) in ["1acceleration", EMPTY_FILE_CHECKSUM]

        renamer.delete_checksum(original_checksum)
        file_without_checksum = tmp_path / "example.txt"
        assert file_without_checksum.exists()
        assert_one_file(tmp_path)
        assert not renamer.has_checksum(file_without_checksum)


def test_file_renamer_write_locked_file_does_nothing(tmp_path, renamer):
    original_file = tmp_path / "example.1acceleration.txt"
    original_file.touch()
    assert renamer.has_checksum(original_file)
    original_checksum = renamer.checksum(original_file)
    assert str(original_checksum) == "1acceleration"

    renamer.write_checksum(Checksum(original_file, "2professional"))
    assert original_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_write_unlocked_file(tmp_path, renamer):
    expectations = {
        "example.txt": "example.2professional.txt",
        "md5.1acceleration": "md5.2professional.1acceleration",
    }
    for original_name, expected_name in expectations.items():
        original_file = tmp_path / original_name
        original_file.touch()
        assert not renamer.has_checksum(original_file)

        renamer.write_checksum(Checksum(original_file, "2professional"))
        renamed_file = tmp_path / expected_name
        assert renamed_file.exists()
        assert_one_file(tmp_path)
        renamed_file.unlink()


def test_file_renamer_delete_unlocked_file_does_nothing(tmp_path, renamer):
    names = ["example.txt", "md5.1acceleration", ".dat.1acceleration"]
    for name in names:
        original_file = tmp_path / name
        original_file.touch()
        assert not renamer.has_checksum(original_file)

        renamer.delete_checksum(Checksum(original_file, "2professional"))
        assert original_file.exists()
        assert_one_file(tmp_path)
        original_file.unlink()


def test_file_renamer_write_unlockable_file_does_nothing(tmp_path, renamer):
    names = [".0intelligence", "md5", ".dat"]
    for name in names:
        original_file = tmp_path / name
        original_file.touch()
        assert not renamer.has_checksum(original_file)

        renamer.write_checksum(Checksum(original_file, "2professional"))
        assert original_file.exists()
        assert_one_file(tmp_path)
        original_file.unlink()


def test_file_renamer_delete_unlockable_file_does_nothing(tmp_path, renamer):
    names = [".0intelligence", "md5", ".dat"]
    for name in names:
        original_file = tmp_path / name
        original_file.touch()
        assert not renamer.has_checksum(original_file)

        renamer.delete_checksum(Checksum(original_file, "2professional"))
        assert original_file.exists()
        assert_one_file(tmp_path)
        original_file.unlink()


def test_file_renamer_checksum_unlocked_file_fails(tmp_path, renamer):
    original_file = tmp_path / "example.txt"
    original_file.touch()
    assert not renamer.has_checksum(original_file)

    with pytest.raises(Exception):
        _ = renamer.checksum(original_file)


def test_file_renamer_checksum_locked_file_multiple_checksums(tmp_path, renamer):
    names = [
        "example.mp4.1acceleration.2professional.jpg",
        "example.0intelligence.mp4.1acceleration.2professional.jpg",
        ".0intelligence.2professional.1acceleration",
    ]
    for name in names:
        original_file = tmp_path / name
        original_file.touch()
        assert renamer.has_checksum(original_file)
        assert renamer.checksum(original_file).value == "2professional"


def test_check_command_correct_checksum(
    mock_presenter, mock_repository, mock_calculator, mocker
):
    # Set up the repository to return the correct checksum
    checksum = Checksum(Path("test_file.txt"), "abc123")
    mock_repository.checksum.return_value = checksum
    mock_calculator.compute_checksums.return_value = iter([checksum])

    # Create the CheckCommand instance
    check_command = CheckCommand(
        presenter=mock_presenter,
        repository=mock_repository,
        calculator=mock_calculator,
        digester=mocker.Mock(),  # Mock the digester for simplicity
        files=[Path("test_file.txt")],
    )

    # Execute the command
    check_command.run()

    # Verify that the ok method of the presenter is called with the correct checksum
    mock_presenter.ok.assert_called_once_with(checksum)


def test_check_command_incorrect_checksum(
    mock_presenter, mock_repository, mock_calculator, mocker
):
    # Set up the repository to return the correct checksum
    checksum = Checksum(Path("test_file.txt"), "abc123")
    wrong_checksum = Checksum(Path("test_file.txt"), "123abc")
    mock_repository.checksum.return_value = wrong_checksum
    mock_calculator.compute_checksums.return_value = iter([checksum])

    # Create the CheckCommand instance
    check_command = CheckCommand(
        presenter=mock_presenter,
        repository=mock_repository,
        calculator=mock_calculator,
        digester=mocker.Mock(),  # Mock the digester for simplicity
        files=[Path("test_file.txt")],
    )

    # Execute the command
    check_command.run()

    # Verify that the ok method of the presenter is called with the correct checksum
    mock_presenter.fail.assert_called_once_with(checksum)


def test_check_command_no_checksum(
    mock_presenter, mock_repository, mock_calculator, mocker
):
    # Set up the repository to return the correct checksum
    checksum = Checksum(Path("test_file.txt"), "abc123")
    mock_repository.has_checksum.return_value = False
    mock_repository.checksum.side_effect = ValueError("No Checksum")
    mock_calculator.compute_checksums.return_value = iter([checksum])

    # Create the CheckCommand instance
    check_command = CheckCommand(
        presenter=mock_presenter,
        repository=mock_repository,
        calculator=mock_calculator,
        digester=mocker.Mock(),  # Mock the digester for simplicity
        files=[Path("test_file.txt")],
    )

    # Execute the command
    check_command.run()

    # Verify that the ok method of the presenter is called with the correct checksum
    mock_presenter.show.assert_called_once_with(checksum)


def test_process_pool_calculator(tmp_path):
    path = tmp_path / "test.txt"
    path.touch()
    calculator = ProcessPoolChecksumCalculator(QuarterSha256Base36Digester())
    results = list(calculator.compute_checksums([path]))

    # Assert the results based on known input and expected output
    assert results == [Checksum(path, EMPTY_FILE_CHECKSUM)]


def assert_one_file(tmp_path):
    assert len(list(tmp_path.glob("*"))) == 1


@pytest.fixture
def mock_presenter(mocker):
    return mocker.Mock(spec=Presenter)


@pytest.fixture
def mock_repository(mocker):
    return mocker.Mock(spec=ChecksumRepository)


@pytest.fixture
def mock_calculator(mocker):
    return mocker.Mock(spec=ChecksumCalculator)


@pytest.fixture
def renamer():
    return FileRenamer(QuarterSha256Base36Digester())
