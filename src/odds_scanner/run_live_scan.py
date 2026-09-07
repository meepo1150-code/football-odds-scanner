from pathlib import Path
from .five_dollar_provider import FiveDollarCurrentProvider
from .scanner import scan


def main():
    result=scan(Path('.'), provider=FiveDollarCurrentProvider())
    print(result)


if __name__ == '__main__':
    main()
