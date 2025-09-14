.PHONY: help install uninstall service-install service-remove

# Usage:
#   make install                 # user install (~/.local)
#   make install MODE=system     # system install (uses sudo)
#   make uninstall               # remove user install
#   make uninstall MODE=system   # remove system install

PACKAGE := labdns
PYTHON  ?= python3
PIP     ?= $(PYTHON) -m pip
# Extra flags passed to pip (e.g., --break-system-packages on Debian/Ubuntu)
PIP_FLAGS ?=
MODE ?= user  # user | system

help:
	@echo "Targets: install, uninstall"
	@echo "Variables: MODE=user|system, PYTHON, PIP, PIP_FLAGS"
	@echo "Examples:"
	@echo "  make install"
	@echo "  make install MODE=system PIP_FLAGS='--break-system-packages'"
	@echo "  make uninstall MODE=system"
	@echo "  make service-install MODE=system"
	@echo "  make service-remove MODE=user"

install:
	@set -e; \
	echo "Installing $(PACKAGE) (MODE=$(MODE))"; \
	if [ "$(MODE)" = "system" ]; then \
		if [ "$$(id -u)" -ne 0 ]; then SUDO=sudo; else SUDO=; fi; \
		$$SUDO $(PIP) install $(PIP_FLAGS) .; \
	else \
		$(PIP) install $(PIP_FLAGS) --user .; \
		echo "Note: ensure $$HOME/.local/bin is in PATH"; \
	fi; \
	echo "Done. Try: labdns version"

uninstall:
	@set -e; \
	echo "Uninstalling $(PACKAGE) (MODE=$(MODE))"; \
	if [ "$(MODE)" = "system" ]; then \
		if [ "$$(id -u)" -ne 0 ]; then SUDO=sudo; else SUDO=; fi; \
		$$SUDO $(PIP) uninstall -y $(PACKAGE); \
	else \
		$(PIP) uninstall -y $(PACKAGE); \
	fi; \
	echo "Done."

service-install:
	@set -e; \
	echo "Installing systemd service (MODE=$(MODE))"; \
	SERVICE_MODE=$(MODE) ./labdns.sh install

service-remove:
	@set -e; \
	echo "Removing systemd service (MODE=$(MODE))"; \
	SERVICE_MODE=$(MODE) ./labdns.sh remove
