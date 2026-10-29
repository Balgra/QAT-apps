from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

DEFAULT_DATA_FILE = Path(__file__).resolve().parent / "data" / "accounts.json"


def main():
    from ui.tk_app import ArgentariaApp

    with TemporaryDirectory(prefix="argentaria-session-") as folder:
        data_file = Path(folder) / "accounts.json"
        copyfile(DEFAULT_DATA_FILE, data_file)
        ArgentariaApp(data_file).run()


if __name__ == "__main__":
    main()

