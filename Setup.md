# Setup

Download or clone QAT-apps and open a terminal in that folder. Choose an application below. No shared Python environment or additional test runner is required.

## Refit

The simplest option on Windows, Linux, or macOS is Docker. Install and start [Docker Desktop or Docker Engine with Compose](https://docs.docker.com/get-started/get-docker/), then run:

```text
cd Refit
docker compose up -d --build --force-recreate
```

Open http://localhost:5173. To stop it, run `docker compose down` from `Refit`. A new backend process starts with 20 listings and no orders. A browser refresh keeps the current run's orders.

For native startup without Docker, see the [Refit README](Refit/README.md#without-docker). It needs Python **3.10+**, Node.js **22.12+** (within the Node 22 release line), and npm.

## Argentaria

Install [Python 3.10 or newer](https://www.python.org/downloads/) with Tcl/Tk. The standard Windows and macOS python.org installers include Tkinter. Then, starting in QAT-apps:

**Windows CMD or PowerShell:**

```text
cd Argentaria
python -m pip install --user -r requirements.txt
python -B app.py
```

If Windows uses `py` instead of `python`, use `py` for both commands.

**macOS or Linux with a Python installation that permits pip installs:**

```bash
cd Argentaria
python3 -m pip install --user -r requirements.txt
python3 -B app.py
```

**Ubuntu/Debian alternative using system packages, without pip:**

```bash
sudo apt update
sudo apt install python3-tk python3-pytest tzdata
cd Argentaria
python3 -B app.py
```

Check that `python3 --version` is at least 3.10. Other Linux distributions use different package names. Argentaria needs a graphical desktop.

Some OS-managed Python installations reject direct pip installs with `externally-managed-environment` ([Python packaging guidance](https://packaging.python.org/en/latest/specifications/externally-managed-environments/)). Use Docker for Refit or the system-package option above for Argentaria on Ubuntu/Debian. A virtual environment remains an optional alternative; it is not a prerequisite for these application instructions. If you choose to use one, omit `--user` when installing dependencies.

Each Argentaria launch starts with the same supplied accounts, balances, cards, and PINs. Close its window to stop it. Account operations and re-inserting a card keep changes within the current run.

The project READMEs include demo credentials, direct pytest commands, and coverage commands.

## SonarQube

Use **SonarQube Community Build in Docker** on Windows, macOS, or Linux to analyse either local project. One SonarQube server hosts both projects; install it once. The server displays results, while the **SonarScanner for Python (`pysonar`)** reads your local source files and sends the analysis to it. The applications do not need to be running for a scan.

### 1. Install and start Docker

Choose the official instructions for your OS:

- [Windows: Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/). Use the WSL 2 backend and Linux containers.
- [macOS: Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/). Choose the installer for Apple silicon or Intel, as appropriate.
- [Linux: Docker Engine](https://docs.docker.com/engine/install/) or [Docker Desktop](https://docs.docker.com/desktop/setup/install/linux/).

Start Docker Desktop, or the Docker service if using Engine. In Windows CMD/PowerShell, Linux Bash, or macOS Zsh, check:

```text
docker version
```

Both **Client** and **Server** details should appear. If Docker is already installed for Refit, reuse it.

### 2. Start SonarQube

Run this command **once**, from any directory. Keep it on one line in every shell:

```text
docker run -d --name qat-sonarqube -p 127.0.0.1:9000:9000 -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true -v qat_sonarqube_data:/opt/sonarqube/data -v qat_sonarqube_extensions:/opt/sonarqube/extensions -v qat_sonarqube_logs:/opt/sonarqube/logs sonarqube:community
```

Docker downloads SonarQube and its runtime; no separate server Java installation is needed. This uses the embedded database and disables Elasticsearch bootstrap checks for this local classroom setup. It is a local evaluation installation, following the [SonarQube quickstart](https://docs.sonarsource.com/sonarqube-community-build/try-out-sonarqube), rather than a production deployment. Named volumes retain the server's projects and analysis history.

The first start can take several minutes. Open **http://localhost:9000**, sign in with username **admin** and password **admin**, and choose a new password when prompted. To inspect startup progress:

```text
docker logs --tail 100 qat-sonarqube
```

For later sessions, reuse the container with `docker start qat-sonarqube`. Stop it with `docker stop qat-sonarqube`. Keep this container, its volumes, and its image version throughout the assignment so your earlier analyses remain available. If you already have SonarQube at port 9000, use that server instead of creating another.

### 3. Create the local projects

In SonarQube, open **Projects → Create project → Create a local project** (some versions label this **Manually**). Create the project you will analyse, or repeat for both:

| Local directory | Project key (`sonar.projectKey`) | Display name (`sonar.projectName`) |
| --- | --- | --- |
| `Refit` | `Refit` | `QAT Refit` |
| `Argentaria` | `Arg` | `QAT Argentaria` |

These values are already defined in each project's **`sonar-project.properties`**. **Keep the key and name exactly as supplied**, including capitalisation. In particular, Argentaria's key is **`Arg`**, not `Argentaria`. Leave these properties unchanged when comparing analyses.

Save the project. If prompted for a new-code definition, accept the default; the assignment's file comparison uses **Overall Code** measures. Choose **Locally** for the analysis method. Generate a **project analysis token** for that project and copy it before leaving the page. Alternatively, generate a project analysis token under **My Account → Security**. Each project's token must authorise analysis of that project; switch tokens when switching projects. Keep tokens out of source files and submissions.

### 4. Install the scanner

Install Python **3.10+** on the computer holding your checkout, including when you run Refit in Docker. Install the scanner once on that computer.

**Windows CMD or PowerShell:**

```text
python -m pip install --user pysonar
```

**Linux/macOS with a Python installation that permits pip installs:**

```bash
python3 -m pip install --user pysonar
```

If your OS reports `externally-managed-environment`, install the scanner with [pipx](https://pipx.pypa.io/latest/how-to/install-pipx.html) instead. On Ubuntu/Debian:

```bash
sudo apt install pipx
pipx install pysonar
pipx ensurepath
```

Open a new terminal after changing PATH. Check the installation with `pysonar --help`. If the command is not found, add the Scripts/bin directory printed by pip to your user PATH, or use pipx and `pipx ensurepath`.

### 5. Set the token and scan

Replace `PASTE_YOUR_PROJECT_TOKEN` with the token for the project you are scanning. Set it in the same terminal where you run the scanner.

**Windows PowerShell:**

```powershell
$env:SONAR_TOKEN = 'PASTE_YOUR_PROJECT_TOKEN'
```

**Windows CMD:**

```bat
set "SONAR_TOKEN=PASTE_YOUR_PROJECT_TOKEN"
```

**Linux Bash/macOS Zsh:**

```bash
export SONAR_TOKEN='PASTE_YOUR_PROJECT_TOKEN'
```

Starting from **QAT-apps**, scan Refit:

```text
cd Refit
pysonar --sonar-host-url=http://localhost:9000
```

Or, starting from **QAT-apps**, scan Argentaria:

```text
cd Argentaria
pysonar --sonar-host-url=http://localhost:9000
```

Run from the application directory containing `sonar-project.properties`, **not** from QAT-apps, Refit/backend, or a tests directory. The scanner reads the project key, name, source/test paths, and coverage path automatically. You do not need to repeat the key on the command line. Initial scans also download scanner components, so allow internet access. See the official [SonarScanner for Python instructions](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/scanners/sonarscanner-for-python).

### 6. View and compare results

After a successful scan, wait for server processing and open the project at **http://localhost:9000**. Use **Code** or **Measures** to inspect individual files. Use **Overall Code**, rather than only **New Code**, for the assignment's table. For Argentaria, compare files in `services`; for Refit, compare files in `backend/app`. The configured scans also include supporting backend files and classify tests separately; Refit's frontend and Argentaria's UI are outside the production-source analysis scope.

After editing/refactoring code, run the same scan command again from the same project directory. Keep the project key, server version, and Python Quality Profile unchanged so the measurements remain comparable. The profile determines which rules produce issues, so record the version and profile used in your report.

**Tests and coverage:** You can scan complexity, duplication, and issues without running tests first. SonarQube does not run tests or generate coverage itself. To include coverage, follow the coverage commands in the [Refit README](Refit/README.md#sonarqube) or [Argentaria README](Argentaria/README.md#sonarqube) **before** scanning. Both properties files expect `coverage.xml` in the application directory. Regenerate it after code changes; an absent or stale report cannot show current coverage. See [SonarQube's Python coverage guide](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/test-coverage/python-test-coverage).

### Common setup problems

- **Docker connection error:** Start Docker Desktop/the Engine service and check `docker version`. On Windows, use Linux containers.
- **Container name already in use:** Run `docker start qat-sonarqube` to reuse the container.
- **Port 9000 already in use:** Reuse your existing SonarQube server. If you choose another host port, use it consistently in the browser and scanner URL.
- **Server does not become available:** Read `docker logs --tail 100 qat-sonarqube`. If Docker reports insufficient memory, increase the resources available to Docker and restart the container.
- **Not authorised:** Check that `SONAR_TOKEN` is set in the scanner terminal and belongs to the selected project on this local server.
- **Coverage arguments are unrecognised:** Install the project's `requirements-test.txt` with the same Python interpreter used to run pytest; it includes `pytest-cov`.
- **Access denied to `.pytest_cache`:** This is a generated-folder permission problem, not a running-app lock. From the directory containing the cache, remove that generated directory using File Explorer or your file manager once permissions allow it. Continue using the documented pytest commands with `-p no:cacheprovider`. Scanner exclusions are already configured, but cannot grant permission to traverse an unreadable directory.


