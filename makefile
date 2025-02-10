# Define the Python interpreter
PYTHON = python

# Define the PostgreSQL data directory
VERSION_POSTGRES = 17
PG_DATA_DIR = "C:\Program Files\PostgreSQL\$(VERSION_POSTGRES)\data"
PG_CTL = "C:\\Program Files\\PostgreSQL\\$(VERSION_POSTGRES)\\bin\\pg_ctl.exe"

# Define the test directory
TEST_DIR = defi_library/unitary

# Define the test command
TEST_CMD = -m unittest discover $(TEST_DIR) -v

# Default target
all: unittest


# Target to run the tests
unittest:
	@echo "Running unit tests..."
	$(PYTHON) $(TEST_CMD)


####################################################


# Target to start the PostgreSQL service
start_postgres:
	@echo "Starting PostgreSQL service..."
	@$(PG_CTL) start -D $(PG_DATA_DIR)

# Target to stop the PostgreSQL service
stop_postgres:
	@echo "Stopping PostgreSQL service..."
	@$(PG_CTL) stop -D $(PG_DATA_DIR)