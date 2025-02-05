import pytest

from backend.models.graph_model import SheetReferences
from backend.models.sheet_model import Column, Sheet, SheetModel


@pytest.fixture
def sample_sheet_model() -> SheetModel:
    """Create a sample sheet model based on the actual data structure."""
    return SheetModel(
        sheets=[
            Sheet(
                name="Reaction",
                columns=[
                    Column(name="well_id", data_type="str"),
                    Column(name="substrates", data_type="str"),
                    Column(name="products", data_type="str"),
                    Column(name="solvent", data_type="str"),
                    Column(name="sampling", data_type="str"),
                ],
            ),
            Sheet(
                name="Molecule",
                columns=[
                    Column(name="cas_id", data_type="str"),
                    Column(name="name", data_type="str"),
                    Column(name="concentration", data_type="float"),
                ],
            ),
            Sheet(
                name="Sampling",
                columns=[
                    Column(name="name", data_type="str"),
                    Column(name="sampling_volume", data_type="float"),
                ],
            ),
        ]
    )


@pytest.fixture
def valid_reference() -> SheetReferences:
    """Create a valid sheet reference based on actual example."""
    return SheetReferences(
        source_sheet_name="Reaction",
        source_column_name="products",
        target_sheet_name="Molecule",
        target_column_name="name",
    )


def test_find_sheet_in_model_success(sample_sheet_model, valid_reference):
    """Test finding an existing sheet."""
    sheet = valid_reference.find_sheet_in_model("Reaction", sample_sheet_model)
    assert sheet.name == "Reaction"
    assert len(sheet.columns) == 5


def test_find_sheet_in_model_not_found(sample_sheet_model, valid_reference):
    """Test finding a non-existent sheet."""
    with pytest.raises(ValueError, match="Sheet NonExistent not found in sheet model"):
        valid_reference.find_sheet_in_model("NonExistent", sample_sheet_model)


def test_find_column_in_sheet_success(sample_sheet_model, valid_reference):
    """Test finding an existing column in a sheet."""
    sheet = valid_reference.find_sheet_in_model("Reaction", sample_sheet_model)
    column = valid_reference.find_column_in_sheet("products", sheet)
    assert column.name == "products"
    assert column.data_type == "str"


def test_find_column_in_sheet_not_found(sample_sheet_model, valid_reference):
    """Test finding a non-existent column."""
    sheet = valid_reference.find_sheet_in_model("Reaction", sample_sheet_model)
    with pytest.raises(
        ValueError, match="Column nonexistent not found in sheet Reaction"
    ):
        valid_reference.find_column_in_sheet("nonexistent", sheet)


def test_compare_to_sheet_valid_reference(sample_sheet_model, valid_reference):
    """Test a valid reference comparison."""
    # Should not raise any exceptions
    valid_reference.compare_to_sheet(sample_sheet_model)


def test_compare_to_sheet_invalid_source_sheet(sample_sheet_model):
    """Test with invalid source sheet."""
    invalid_reference = SheetReferences(
        source_sheet_name="NonExistent",
        source_column_name="products",
        target_sheet_name="Molecule",
        target_column_name="name",
    )
    with pytest.raises(ValueError, match="Sheet NonExistent not found in sheet model"):
        invalid_reference.compare_to_sheet(sample_sheet_model)


def test_compare_to_sheet_invalid_target_sheet(sample_sheet_model):
    """Test with invalid target sheet."""
    invalid_reference = SheetReferences(
        source_sheet_name="Reaction",
        source_column_name="products",
        target_sheet_name="NonExistent",
        target_column_name="name",
    )
    with pytest.raises(ValueError, match="Sheet NonExistent not found in sheet model"):
        invalid_reference.compare_to_sheet(sample_sheet_model)


def test_compare_to_sheet_invalid_source_column(sample_sheet_model):
    """Test with invalid source column."""
    invalid_reference = SheetReferences(
        source_sheet_name="Reaction",
        source_column_name="nonexistent",
        target_sheet_name="Molecule",
        target_column_name="name",
    )
    with pytest.raises(
        ValueError, match="Column nonexistent not found in sheet Reaction"
    ):
        invalid_reference.compare_to_sheet(sample_sheet_model)


def test_compare_to_sheet_invalid_target_column(sample_sheet_model):
    """Test with invalid target column."""
    invalid_reference = SheetReferences(
        source_sheet_name="Reaction",
        source_column_name="products",
        target_sheet_name="Molecule",
        target_column_name="nonexistent",
    )
    with pytest.raises(
        ValueError, match="Column nonexistent not found in sheet Molecule"
    ):
        invalid_reference.compare_to_sheet(sample_sheet_model)
