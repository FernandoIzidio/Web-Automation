import requests, bs4, sys, pathlib
from urllib.parse import urljoin
from typing import Any, IO

WARNINGS = []
PARENT_PACKAGES = []
BASEDIR = pathlib.Path(__file__).parent
STANDARD_PROVIDER = BASEDIR / "Standard_Providers"
STANDARD_PROVIDER.mkdir(exist_ok=True)


LOCAL_PROVIDER = pathlib.Path(__file__).parent / "Local_Providers"
LOCAL_PROVIDER.mkdir(exist_ok=True)

logfile = open((BASEDIR / "log.txt").__str__(), "w")
sys.stdout = logfile


def get_response(url: str) -> requests.Response | None:
    """This function will do a request in the provided route, and return the response, or to print the REJECTED in log file

    Parameters:
    -----------
        url (str): route to make a request


    Returns:
    --------
        requests.Response | None: - Returns the request response
    """

    response = requests.get(url)
    if response.status_code == 200:
        return response
    else:
        print("REJECTED")


def open_context_file(path: str, mode: str = "w") -> IO:
    """This function will open a file_object in provided path. The open mode of fileobject by default is write

    Parameters:
    -----------
        path (str): path which to want open a file_object
        mode (str, optional): open mode of file_object

    Returns:
    --------
        IO[Any]: Returns a file object
    """
    pathlib.Path(path).touch(exist_ok=True)
    contextfile = open(path, mode)
    return contextfile


def extract_module_name(url: str) -> str:
    """This functions returns a valid python module name,  from a url string

    Parameters:
    -----------
        url (str): route or name which to want to extract the python module name

    Returns:
    --------
        str: valid python module name
    """

    url = url.replace(".html", "").split("/")
    PARENT_PACKAGES.append(url[-1])
    url = "".join(url).split(".")[-1]
    return url + ".py"


def get_tags(
    content: str,
    parser: str,
    tag_name: str,
    **attrs,
) -> list | None:
    """
    This function will extract all tags with the provided tag_name and attrs from the content using BeautifulSoup.

    Parameters:
    -----------
    content (str): The content to extract the tags from.
    parser (str): The parser to use when parsing the content.
    tag_name (str): The tag name to extract.
    **attrs (dict): The attributes of the tags to extract.

    Returns:
    --------
    list: A list of tags that were found, or None if no tags were found.

    """
    web = bs4.BeautifulSoup(content, parser)
    tags = web.find_all(tag_name, **attrs)

    if tags:
        return tags


def get_tags_attrs_values(
    content: str,
    parser: str,
    tag_name: str,
    response: requests.Response = None,
    **attrs,
) -> set[str]:
    """
    This function will extract all tags with the provided tag_name and attrs from the content using BeautifulSoup.

    Parameters:
    -----------
    content (str): The content to extract the tags from.
    parser (str): The parser to use when parsing the content.
    tag_name (str): The tag name to extract.
    response (requests.Response, optional): The response object.
    **attrs (dict): The attributes of the tags to extract.

    Returns:
    --------
    set: A set of tags that were found, or None if no tags were found.

    """
    web = bs4.BeautifulSoup(content, parser)
    tags = web.find_all(tag_name, **attrs)

    if tags:
        data = set()
        attribute = attrs.keys()

        data.update(
            [
                urljoin(response.url, tag.get(attr)) if response else tag.get(attr)
                for tag in tags
                for attr in attribute
            ]
        )

        return data


def get_tags_contents(
    content: str,
    parser: str,
    tag_name: str,
    **attrs,
) -> list[str] | None:
    """
    This function will extract all text contents from tags with the provided tag_name and attrs from the content using BeautifulSoup.

    Parameters:
    -----------
    content (str): The content to extract the tags from.
    parser (str): The parser to use when parsing the content.
    tag_name (str): The tag name to extract.
    **attrs (dict): The attributes of the tags to extract.

    Returns:
    --------
    list: A list of tags that were found, or None if no tags were found.

    """
    tags = get_tags(content, parser, tag_name, **attrs)
    data = [tag.text for tag in tags]
    return data


def normalize_name(
    name: str, replace_chars: list[tuple[str]], invalid_chars: dict[int, str]
) -> str:
    """
    This function replaces characters in a string with other characters, and removes unwanted characters from the string.

    Parameters:
    -----------
    name (str): The string to normalize.
    replace_chars (list[tuple[str]]): A list of tuples containing the characters to replace, and the characters to replace them with.
    invalid_chars (dict[int, str]): A dictionary containing the ASCII code of the unwanted characters, and the characters to replace them with.

    Returns:
    --------
    str: The normalized string.

    """
    for tuple in replace_chars:
        name = name.replace(tuple[0], tuple[1])

    return name.translate(invalid_chars).strip()


def refactory_class_names(name: str) -> str:
    """
    This function replaces the class name with a valid python code,
    if the class name is a valid python module.

    Parameters:
    -----------
    name (str): The class name to refactory.

    Returns:
    --------
    str: A valid python code with the class name.
    """
    package_import = (
        name.replace("(generator: Any)", "")
        .replace("(*args, **kwargs)", "")
        .split("class ")
    )
    aux = "".join(package_import).split(".")
    package = aux.pop()
    main_import = ".".join(aux).strip()

    if main_import:
        command = f"""from {main_import} import {package}
class {package}:\n
"""

        return command

    return name + ":\n"


def refactory_function_names(name: str, fd) -> str:
    """
    This function replaces the function name with a valid python code,
    if the function name is a valid python function.

    Parameters:
    -----------
    name (str): The function name to refactory.
    fd (file_object): The file_object where the function is located.

    Returns:
    --------
    str: A valid python code with the function name.
    """

    # Use uma expressão regular para extrair o nome da classe

    if "<" in name:
        name = name.replace("<class", "").replace(">", "", 1)

    letters = [letter for letter in name]
    pos = letters.index("(") + 1
    letters.insert(pos, "self, ")
    letters = "".join(letters)
    name = "def " + letters
    name = name.replace("static ", "")
    if name[-1] == ")":
        return "\t" + name + ":...\n\n"

    temp = [l for l in name.strip()]

    temp.append(": ...\n\n")

    return "\t" + "".join(temp)


def get_object_signature(response: requests.Response) -> list[str]:
    """
    This function will extract all signature of the objects in the documentation

    Parameters:
    ----------
        response: requests.Response
            The requests response object

    Returns:
    -------
        list[str]
            A list of objects signatures

    """

    objects: list[str] = get_tags_contents(
        response.text,
        "html.parser",
        "dt",
        id=lambda id: id and "faker" in id,
    )
    return objects


def write_in_file(data: list, fd):
    """Write many lines of a data object in a fd provided.
    WARNING! This functions will close the file_object

    parameters
    ----------
        data: Iterable
            List of rows to write in file

        fd : file_object - process in execution, which can be writable
            file_object

    returns
    -------
        None




    """
    for obj in data:
        if obj:
            name = normalize_name(obj, [("→", "->")], str.maketrans("", "", "¶"))

            if name.strip().startswith("class"):
                name = refactory_class_names(name)
            else:
                name = refactory_function_names(name, fd)

            fd.write(name)

    fd.close()


if __name__ == "__main__":
    response = get_response("https://faker.readthedocs.io/en/master/providers.html")

    routes: list[str] = get_tags_attrs_values(
        response.text,
        "html.parser",
        "a",
        response,
        href=lambda href: href and "faker.providers" in href and "#" not in href,
    )
    print("Page Requests Standard_Providers:")
    print("\t", *routes, sep="\n\t")

    for route in routes:
        response = get_response(route)
        package_name = extract_module_name(route)
        file_object = open_context_file((STANDARD_PROVIDER / package_name).__str__())

        objects = get_object_signature(response)

        write_in_file(objects, file_object)

    response = get_response("https://faker.readthedocs.io/en/master/locales.html")

    routes = get_tags_attrs_values(
        response.text,
        "html.parser",
        "a",
        response,
        href=lambda href: href and "#" not in href and "locales" in href,
    )

    print("\nPage Requests Local_Providers:")
    print("\t", *routes, sep="\n\t")

    for route in routes:
        response = get_response(route)

        package_name = extract_module_name(route)

        file_object = open_context_file((LOCAL_PROVIDER / package_name).__str__())

        objects = get_object_signature(response)

        write_in_file(objects, file_object)

print("\nParent Packages: \n\n\t", *PARENT_PACKAGES, sep="\n\n\t")

print("\nWARNINGS: \n", *WARNINGS, sep="\n\n")

print("\nWarning lines can be lines that contain objects thats cause errors")

logfile.close()
