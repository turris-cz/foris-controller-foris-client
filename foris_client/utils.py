import re
import typing


def read_passwd_file(path: str) -> typing.Tuple[str]:
    """ Returns username and password from passwd file
    """
    with open(path, "r") as f:
        return re.match(r"^([^:]+):(.*)$", f.readlines()[0][:-1]).groups()
