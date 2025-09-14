# **Project: labDNS 3.0**

**Vision:** To create a modern, lightweight, and extensible DNS server in Python 3. It will be RFC-compliant, manageable via a CLI (with a simple GUI wrapper) using standard zonefiles, and easy to deploy.

**Technology Stack:**
* **Backend:** Python 3.10+
* **DNS Handling:** `dnslib`
* **Zonefile Parsing:** `dnspython`
* **CLI:** `click`
* **GUI Wrapper:** `zenity` or `yad` (and shell scripting)
* **Containerization:** Docker & Docker Compose
* **Packaging:** PyPI

---
### Epic 1: Core DNS Protocol Engine

This epic covers the fundamental functionality of listening for and responding to DNS queries.

#### **User Story 1.1: Basic DNS Query Resolution**
**As a** network client, **I want** to send A and AAAA queries to labDNS, **so that** I can resolve hostnames to their IP addresses.

* **Story Points:** 8
* **Definition of Ready:**
    * Core project structure is established.
    * `dnslib` and `dnspython` are added as dependencies.
* **Definition of Done:**
    * The server listens on UDP port 53.
    * The server correctly responds to A/AAAA queries based on records from a zonefile.
    * Unit tests for query parsing and response generation pass.
* **Acceptance Criteria:**
    * Given a query for a valid hostname, the server returns the correct IP address.
    * The server returns an `NXDOMAIN` error for non-existent records.
    * Responses are compliant with RFC 1035.

* **Tasks:**
    * [ ] **Task 1.1.1: Implement UDP Socket Server**
    * [ ] **Task 1.1.2: Implement DNS Packet Handling**
    * [ ] **Task 1.1.3: Create Unit Tests**

---
### Epic 2: Configuration & Management

This epic focuses on making the server configurable and managing its operation via the command line.

#### **User Story 2.1: Standard Zonefile Support**
**As a** system administrator, **I want** to define DNS records using standard BIND-style zonefiles, **so that** I can use existing tools and knowledge to manage DNS zones.

* **Story Points:** 8
* **Definition of Ready:**
    * The core DNS resolver logic is in place.
* **Definition of Done:**
    * The server can load and parse a standard zonefile on startup.
    * The resolver serves all common record types (A, AAAA, CNAME, MX, TXT, SOA, NS).
    * The application logs clear errors for zonefile syntax errors.
* **Acceptance Criteria:**
    * The server correctly loads a zonefile containing a mix of common record types.
    * DNS queries for any record type in the file are answered correctly.
    * Server start-up fails with a descriptive message for a malformed zonefile.

* **Tasks:**
    * [ ] **Task 2.1.1: Implement Zonefile Loader**
    * [ ] **Task 2.1.2: Integrate Loader with Resolver**

#### **User Story 2.2: Command-Line Interface for Server Management**
**As a** system administrator, **I want** a CLI to control the labDNS server, **so that** I can start it, check configuration, and reload zones without a full restart.

* **Story Points:** 5
* **Definition of Ready:**
    * The zonefile loading mechanism is complete.
    * The `click` library is added to the project.
* **Definition of Done:**
    * The application is runnable via a `labdns` entry point.
    * A `labdns start --zonefile <path>` command starts the server.
    * A `labdns check --zonefile <path>` command validates the zonefile.
    * The running server can reload its zonefile upon receiving a `SIGHUP` signal.
* **Acceptance Criteria:**
    * `labdns start` successfully initiates the DNS server.
    * `labdns check` on a valid zonefile returns exit code 0.
    * `labdns check` on an invalid zonefile returns an error and a non-zero exit code.
    * Sending `SIGHUP` to the server process causes it to reload the zonefile.

* **Tasks:**
    * [ ] **Task 2.2.1: Implement CLI Structure with Click**
    * [ ] **Task 2.2.2: Implement Command Logic**
    * [ ] **Task 2.2.3: Implement Graceful Reload**

---
### Epic 3: Deployment & Packaging

This epic focuses on making labDNS easy to install and run in various environments.

#### **User Story 3.1: Containerize the Application**
**As a** DevOps engineer, **I want** a Docker image for labDNS, **so that** I can deploy it consistently.

* **Story Points:** 5
* **Definition of Ready:**
    * The application has a clear CLI entry point.
* **Definition of Done:**
    * A `Dockerfile` is present in the repository.
    * A `docker-compose.yml` file is provided for easy local testing.
* **Acceptance Criteria:**
    * `docker build -t labdns .` completes successfully.
    * `docker-compose up` starts the server correctly.
    * The containerized server responds to DNS queries.
    * Zonefiles can be mounted into the container via a volume.

* **Tasks:**
    * [ ] **Task 3.1.1: Write a Dockerfile**
    * [ ] **Task 3.1.2: Create a Docker Compose File**

---
### Epic 4: Desktop GUI Wrapper

This epic adds a simple graphical interface that acts as a front-end for the CLI, making it more accessible to desktop users.  GUI for the CLI.

#### **User Story 4.1: GUI for Server Operations**
**As a** desktop administrator, **I want** a simple GUI to start the server and check my zonefile, **so that** I don't have to use the command line for basic operations.

* **Story Points:** 5
* **Definition of Ready:**
    * The CLI (Epic 2) is fully implemented and functional.
    * `zenity` or `yad` is documented as a dependency for the GUI wrapper.
* **Definition of Done:**
    * An executable shell script is created that uses `zenity`/`yad` to provide a GUI.
    * The GUI can successfully construct and execute `labdns start` and `labdns check` commands.
    * A `.desktop` file is included for easy integration with application menus.
* **Acceptance Criteria:**
    * A "Start Server" option opens a file dialog to select a zonefile. On confirmation, it opens a new terminal window running the `labdns start` command.
    * A "Check Zonefile" option opens a file dialog. On confirmation, it runs the `labdns check` command and displays the success or error output in a message box.
    * Canceling a file dialog returns the user to the main menu without executing a command.

* **Tasks:**
    * [ ] **Task 4.1.1: Implement Main Menu Script**
        * [ ] Subtask 4.1.1.1: Create a script that shows the main options ("Start Server", "Check Zonefile") using a `zenity --list` dialog.
    * [ ] **Task 4.1.2: Implement "Start Server" Logic**
        * [ ] Subtask 4.1.2.1: Use `zenity --file-selection` to get the zonefile path.
        * [ ] Subtask 4.1.2.2: Launch a terminal emulator (e.g., `gnome-terminal`) to execute the `labdns start` command with the selected path.
    * [ ] **Task 4.1.3: Implement "Check Zonefile" Logic**
        * [ ] Subtask 4.1.3.1: Use `zenity --file-selection` to get the path.
        * [ ] Subtask 4.1.3.2: Execute the `labdns check` command and capture its output.
        * [ ] Subtask 4.1.3.3: Use `zenity --info` or `zenity --error` to display the result.
    * [ ] **Task 4.1.4: Create `.desktop` File**
        * [ ] Subtask 4.1.4.1: Write a desktop entry file so the script appears in desktop application launchers.
