from pathlib import Path

from .oddspapi_current_provider import OddsPapiCurrentProvider
from .scanner import scan


def main():
    result = scan(Path("."), provider=OddsPapiCurrentProvider())
    print(result)


if __name__ == "__main__":
    main()
