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


def test_file_renamer_delete_rename_file_with_checksum_in_stem(tmp_path, renamer):
    original_file = tmp_path / "example.abcd1234efgh5.txt"
    original_file.touch()
    assert renamer.has_checksum(original_file)
    original_checksum = renamer.checksum(original_file)
    assert str(original_checksum) == "abcd1234efgh5"

    renamer.delete_checksum(original_checksum)
    file_without_checksum = tmp_path / "example.txt"
    assert file_without_checksum.exists()
    assert_one_file(tmp_path)
    assert not renamer.has_checksum(file_without_checksum)


def test_file_renamer_write_do_not_rename_file_with_checksum_in_stem(tmp_path, renamer):
    original_file = tmp_path / "example.abcd1234efgh5.txt"
    original_file.touch()
    assert renamer.has_checksum(original_file)
    original_checksum = renamer.checksum(original_file)
    assert str(original_checksum) == "abcd1234efgh5"

    renamer.write_checksum(Checksum(original_file, "newchecksum01"))
    assert original_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_write_rename_file_without_checksum_in_stem(tmp_path, renamer):
    original_file = tmp_path / "example.txt"
    original_file.touch()
    assert not renamer.has_checksum(original_file)

    renamer.write_checksum(Checksum(original_file, "newchecksum01"))
    renamed_file = tmp_path / "example.newchecksum01.txt"
    assert renamed_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_delete_do_not_rename_file_without_checksum_in_stem(
    tmp_path, renamer
):
    original_file = tmp_path / "example.txt"
    original_file.touch()
    assert not renamer.has_checksum(original_file)

    renamer.delete_checksum(Checksum(original_file, "newchecksum01"))
    assert original_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_write_rename_file_without_extension_without_checksum_in_suffix(
    tmp_path, renamer
):
    original_file = tmp_path / "md5"
    original_file.touch()
    assert not renamer.has_checksum(original_file)

    renamer.write_checksum(Checksum(original_file, "newchecksum01"))
    renamed_file = tmp_path / "md5.newchecksum01"
    assert renamed_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_delete_do_not_rename_file_without_extension_without_checksum_in_suffix(
    tmp_path, renamer
):
    original_file = tmp_path / "md5"
    original_file.touch()
    assert not renamer.has_checksum(original_file)

    renamer.delete_checksum(Checksum(original_file, "newchecksum01"))
    assert original_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_delete_rename_file_without_extension_with_checksum_in_suffix(
    tmp_path, renamer
):
    original_file = tmp_path / "md5.abcd1234efgh5"
    original_file.touch()
    assert renamer.has_checksum(original_file)
    original_checksum = renamer.checksum(original_file)
    assert str(original_checksum) == "abcd1234efgh5"

    renamer.delete_checksum(original_checksum)
    file_without_checksum = tmp_path / "md5"
    assert file_without_checksum.exists()
    assert_one_file(tmp_path)
    assert not renamer.has_checksum(file_without_checksum)


def test_file_renamer_write_do_not_rename_file_without_extension_with_checksum_in_suffix(
    tmp_path, renamer
):
    original_file = tmp_path / "md5.abcd1234efgh5"
    original_file.touch()
    assert renamer.has_checksum(original_file)
    original_checksum = renamer.checksum(original_file)
    assert str(original_checksum) == "abcd1234efgh5"

    renamer.write_checksum(Checksum(original_file, "newchecksum01"))
    assert original_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_write_rename_file_name_is_suffix_without_checksum(
    tmp_path, renamer
):
    original_file = tmp_path / ".dat"
    original_file.touch()
    assert not renamer.has_checksum(original_file)

    renamer.write_checksum(Checksum(original_file, "newchecksum01"))
    renamed_file = tmp_path / ".dat.newchecksum01"
    assert renamed_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_delete_rename_file_name_is_suffix_with_checksum(
    tmp_path, renamer
):
    original_file = tmp_path / ".dat.abcd1234efgh5"
    original_file.touch()
    assert renamer.has_checksum(original_file)
    original_checksum = renamer.checksum(original_file)

    renamer.delete_checksum(original_checksum)
    renamed_file = tmp_path / ".dat"
    assert renamed_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_write_do_not_rename_file_name_is_suffix_same_size_as_checksum(
    tmp_path, renamer
):
    original_file = tmp_path / ".factorization"
    original_file.touch()
    assert renamer.has_checksum(original_file)
    assert str(renamer.checksum(original_file)) == "factorization"

    renamer.write_checksum(Checksum(original_file, "newchecksum01"))
    assert original_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_delete_do_not_rename_file_name_is_suffix_same_size_as_checksum(
    tmp_path, renamer
):
    original_file = tmp_path / ".factorization"
    original_file.touch()
    assert renamer.has_checksum(original_file)
    original_checksum = renamer.checksum(original_file)
    assert str(original_checksum) == "factorization"

    renamer.delete_checksum(original_checksum)
    assert original_file.exists()
    assert_one_file(tmp_path)


def test_file_renamer_checksum_fail_for_file_without_checksum(tmp_path, renamer):
    original_file = tmp_path / "example.txt"
    original_file.touch()
    assert not renamer.has_checksum(original_file)

    with pytest.raises(Exception):
        _ = renamer.checksum(original_file)


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
    assert results == [Checksum(path, "3gng7kheu33tg")]


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
