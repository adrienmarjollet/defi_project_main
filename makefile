# Define the Python interpreter
PYTHON = python

# Define the test directory
TEST_DIR = python/unitary

# Define the test command
TEST_CMD = -m unittest discover $(TEST_DIR)

# Default target
all: unittest

# Target to run the tests
unittest:
    @echo "Running unit tests..."
    $(PYTHON) $(TEST_CMD)


