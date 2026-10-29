# Setup

Download or clone QAT-apps and open a terminal in that folder. Choose an application below. No shared Python environment or additional test runner is required.

## Refit

The simplest option on Windows, Linux, or macOS is Docker. Install and start [Docker Desktop or Docker Engine with Compose](https://docs.docker.com/get-started/get-docker/), then run:

```text
cd Refit
docker compose up -d --build --force-recreate
```

Open http://localhost:5173. To stop it, run `docker compose down` from `Refit`. A new backend process starts with 20 listings and no orders. A browser refresh keeps the current run's orders.

For native startup without Docker, see the [Refit README](Refit/README.md#without-docker). It needs Python **3.10+**, Node.js 22, and npm.

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

The project READMEs include demo credentials, direct pytest commands, and optional SonarQube/coverage commands.


