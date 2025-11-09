# Running Tests Locally

## Prerequisites

Make sure you have the required dependencies installed. You can install them using one of these methods:

### Option 1: Install dev dependencies from pyproject.toml (Recommended)

```bash
cd /path/to/comfyui-save-file-extended
pip install -e ".[dev]"
```

This will install:

-   pytest and pytest-cov (testing framework)
-   torch, torchaudio, numpy, pillow (for creating test data)
-   All other dev dependencies

### Option 2: Install pytest and test dependencies manually

```bash
pip install pytest pytest-cov torch torchaudio numpy pillow av
```

## Running Tests

### Run all tests

From the project root directory:

```bash
pytest tests/
```

Or from the `tests/` directory:

```bash
cd tests
pytest
```

### Run with verbose output

```bash
pytest tests/ -v
```

### Run a specific test file

```bash
# Audio tests
pytest tests/test_save_audio_extended.py

# Image tests
pytest tests/test_save_image_extended.py

# Video tests
pytest tests/test_save_video_extended.py
```

### Run a specific test class

```bash
# Example: Run all SaveAudioExtended tests
pytest tests/test_save_audio_extended.py::TestSaveAudioExtended

# Example: Run all SaveVideoExtended tests
pytest tests/test_save_video_extended.py::TestSaveVideoExtended
```

### Run a specific test method

```bash
# Example: Run a single test
pytest tests/test_save_audio_extended.py::TestSaveAudioExtended::test_filename_parameter_single_file
```

### Run with coverage report

```bash
pytest tests/ --cov=src/comfyui_save_file_extended --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`. Open it in your browser to see detailed coverage information.

### Run with coverage (terminal output)

```bash
pytest tests/ --cov=src/comfyui_save_file_extended --cov-report=term-missing
```

### Run tests and stop on first failure

```bash
pytest tests/ -x
```

### Run tests and show print statements

```bash
pytest tests/ -s
```

### Run tests in parallel (faster)

```bash
pip install pytest-xdist
pytest tests/ -n auto
```

This will automatically detect the number of CPU cores and run tests in parallel.

## Test Structure

The tests are organized into separate files by node type:

-   **`conftest.py`** - Shared fixtures, mocks, and test setup

    -   All ComfyUI module mocks
    -   Test fixtures (temp_dir, mock_audio_data, mock_image_data, mock_video_data)
    -   Node fixtures (save_audio_node, save_image_node, save_webm_node, save_video_node)

-   **`test_save_audio_extended.py`** - Tests for audio nodes

    -   `TestSaveAudioExtended` - Main audio save node tests (11 tests)
    -   `TestSaveAudioMP3Extended` - MP3-specific node tests (3 tests)
    -   `TestSaveAudioOpusExtended` - Opus-specific node tests (3 tests)

-   **`test_save_image_extended.py`** - Tests for image nodes

    -   `TestSaveImageExtended` - Image save node tests (10 tests)

-   **`test_save_video_extended.py`** - Tests for video nodes

    -   `TestSaveWEBMExtended` - WEBM-specific node tests (6 tests)
    -   `TestSaveVideoExtended` - General video save node tests (11 tests)

-   **`pytest.ini`** - Pytest configuration file

## Test Coverage

The test suite covers:

-   ✅ Filename handling (with/without extension, priority, whitespace)
-   ✅ Custom filename fallback
-   ✅ UUID-based filename generation
-   ✅ Batch processing
-   ✅ Input validation (including cloud requirements)
-   ✅ Local folder paths
-   ✅ Cloud upload functionality
-   ✅ Metadata handling (prompt, extra_pnginfo)
-   ✅ Format-specific validation (MP3, Opus quality options)

## Common Issues

### Import errors

If you encounter import errors, make sure you're running from the project root and that the Python path is set correctly. The `conftest.py` file should handle path setup automatically.

### Missing dependencies

If tests fail due to missing packages, install them:

```bash
pip install torch torchaudio pillow numpy av pytest pytest-cov
```

### Mock-related issues

The tests use extensive mocking for ComfyUI-specific modules. All mocks are set up in `conftest.py` before any node imports. If you see errors related to mocks, check that:

1. You're running tests from the project root
2. The `conftest.py` file is in the `tests/` directory
3. All ComfyUI imports are properly mocked

### Module not found errors

If you see "ModuleNotFoundError", ensure you've installed the package in editable mode:

```bash
pip install -e ".[dev]"
```

## Example Output

When tests run successfully, you should see output like:

```
======================== test session starts ========================
platform darwin -- Python 3.12.10, pytest-9.0.0, pluggy-1.6.0
rootdir: /path/to/comfyui-save-file-extended/tests
configfile: pytest.ini
plugins: anyio-4.10.0
collected 44 items

tests/test_save_audio_extended.py ................. [ 38%]
tests/test_save_image_extended.py .......... [ 61%]
tests/test_save_video_extended.py ................. [100%]

======================== 44 passed in 1.68s ========================
```

## Quick Test Commands

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run only audio tests
pytest tests/test_save_audio_extended.py -v

# Run only image tests
pytest tests/test_save_image_extended.py -v

# Run only video tests
pytest tests/test_save_video_extended.py -v

# Run with coverage
pytest tests/ --cov=src/comfyui_save_file_extended --cov-report=term-missing

# Run and stop on first failure
pytest tests/ -x

# Run in parallel (faster)
pytest tests/ -n auto
```
