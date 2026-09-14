import re
from pathlib import Path

import dill
import yaml

from nice import ROOT_DIR


def make_unique_folder_name(parent_folder: str | Path, proposed_dirname: str):
    """Generate a folder that does not already exist in a user-defined parent folder.

    Args:
        parent_folder (str | Path): directory that a folder is expected to be created in.
        proposed_dirname (str): folder name to check for existence and
            to use as the base folder description of a new an unique folder name.

    Returns:
        str: unique direcoty that does not yet exist in parent_folder.
    """

    # if folder(s) exist with the same base name, make a new unique directory name
    # file_base = proposed_fname.split(fext)[0]
    existing_files = [
        f for f in Path(parent_folder).glob(f"**/{proposed_dirname}*") if f.is_dir()
    ]
    if len(existing_files) == 0:
        return Path(parent_folder) / proposed_dirname

    # get past numbers that were used to make unique folders by matching
    # folder names against the file base name followed by a number
    past_numbers = [
        int(
            re.findall(f"{proposed_dirname}[0-9]+", str(fname))[0].split(
                proposed_dirname
            )[-1]
        )
        for fname in existing_files
        if len(re.findall(f"{proposed_dirname}[0-9]+", str(fname))) > 0
    ]

    if len(past_numbers) > 0:
        # if multiple folders have the same basename followed by a number,
        # take the maximum unique number and add one
        unique_number = int(max(past_numbers) + 1)
        return Path(parent_folder) / f"{proposed_dirname}{unique_number}"
    else:
        # if no folders have the same basename followed by a number,
        # but do have the same basename, then add a zero to the folder basename
        return Path(parent_folder) / f"{proposed_dirname}0"


def check_create_folder(filepath):
    if Path(filepath).is_file():
        filepath = Path(filepath).parent

    if not Path(filepath).is_dir():
        Path(filepath).mkdir(exist_ok=True, parents=True)

    return


def dump_data_to_pickle(data, filepath):
    with open(filepath, "wb") as f:
        dill.dump(data, f)


def load_dill_pickle(filepath):
    with open(filepath, "rb") as f:
        data = dill.load(f)
    return data


def write_yaml(filename, data):
    if ".yaml" not in str(filename):
        filename = filename + ".yaml"

    with open(filename, "w+") as file:
        yaml.dump(data, file, sort_keys=False, encoding=None, default_flow_style=False)


def get_path(path: str | Path) -> Path:
    """
    Convert a string or Path object to an absolute Path object, prioritizing different locations.

    This function attempts to find the existence of a path in the following order:
    1. As an absolute path.
    2. Relative to the current working directory.
    3. Relative to the H2Integrate package.

    Args:
        path (str | Path): The input path, either as a string or a Path object.

    Raises:
        FileNotFoundError: If the path is not found in any of the locations.

    Returns:
        Path: The absolute path to the file.
    """
    # Store the original path for reference in error messages.
    original_path = path

    # If the input is a string, convert it to a Path object.
    if isinstance(path, str):
        path = Path(path)

    # Check if the path exists as an absolute path.
    if path.exists():
        return path.absolute()

    # If not, try finding the path relative to the current working directory.
    relative_path = Path.cwd() / path
    path = relative_path

    # If the path still doesn't exist, attempt to find it relative to the H2Integrate package.
    if path.exists():
        return path.absolute()

    # Determine the path relative to the H2Integrate package.
    h2i_based_path = ROOT_DIR.parent / Path(original_path)

    path = h2i_based_path

    if path.exists():
        return path.absolute()

    # If the path still doesn't exist in any of the prioritized locations, raise an error.
    raise FileNotFoundError(
        f"File not found in absolute path: {original_path}, relative path: "
        f"{relative_path}, or H2Integrate-based path: "
        f"{h2i_based_path}"
    )


def find_file(filename: str | Path, root_folder: str | Path | None = None):
    """
    This function attempts to find a filepath matching `filename` from a variety of locations
    in the following order:

    1. Relative to the root_folder (if provided)
    2. Relative to the current working directory.
    3. Relative to the H2Integrate package.
    4. As an absolute path if `filename` is already absolute

    Args:
        filename (str | Path): Input filepath
        root_folder (str | Path, optional): Root directory to search for filename in.
            Defaults to None.

    Raises:
        FileNotFoundError: If the path is not found in any of the locations.

    Returns:
        Path: The absolute path to the file.
    """

    # 1. check for file in the root directory
    files = []
    if root_folder is not None:
        root_folder = Path(root_folder)
        # if the file exists in the root directory, return full path
        if Path(root_folder, filename).exists():
            return Path(root_folder, filename).resolve().absolute()

        # check for files within root directory
        files = list(Path(root_folder).glob(f"**/{filename}"))

        if len(files) == 1:
            return files[0].absolute()
        if len(files) > 1:
            raise FileNotFoundError(
                f"Found {len(files)} files in the root directory ({root_folder}) that have "
                f"filename {filename}"
            )

        filename_no_rel = "/".join(
            p
            for p in Path(root_folder, filename).resolve(strict=False).parts
            if p not in Path(root_folder).parts
        )
        files = list(Path(root_folder).glob(f"**/{filename_no_rel}"))
        if len(files) == 1:
            return files[0].absolute()

    # 2. check for file relative to the current working directory
    files_cwd = list(Path.cwd().glob(f"**/{filename}"))
    if len(files_cwd) == 1:
        return files_cwd[0].absolute()

    # 3. check for file relative to the ICE package root
    files_h2i = list(ROOT_DIR.parent.glob(f"**/{filename}"))
    files_h2i = [file for file in files_h2i if "build" not in file.parts]
    if len(files_h2i) == 1:
        return files_h2i[0].absolute()

    # 4. check for as absolute path
    if Path(filename).is_absolute():
        return Path(filename)

    if len(files_cwd) == 0 and len(files_h2i) == 0:
        raise FileNotFoundError(
            f"Did not find any files matching {filename} in the current working directory "
            f"{Path.cwd()} or relative to the ICE package {ROOT_DIR.parent}"
        )
    if root_folder is not None and len(files) == 0:
        raise FileNotFoundError(
            f"Did not find any files matching {filename} in the current working directory "
            f"{Path.cwd()}, relative to the H2Integrate package {ROOT_DIR.parent}, or relative to "
            f"the root directory {root_folder}."
        )
    raise ValueError(
        f"Cannot find unique file: found {len(files_cwd)} files relative to cwd, "
        f"{len(files_h2i)} files relative to H2Integrate root directory, "
        f"{len(files)} files relative to the root folder."
    )


class Loader(yaml.SafeLoader):
    def __init__(self, stream):
        # root is the parent directory of the parent yaml file
        self._root = get_path(Path(stream.name).parent)

        super().__init__(stream)

    def include(self, node):
        filename = find_file(node.value, self._root)

        return load_yaml(filename)


Loader.add_constructor("!include", Loader.include)


def load_yaml(filename, loader=Loader) -> dict:
    if isinstance(filename, dict):
        return filename  # filename already yaml dict
    with Path.open(filename) as fid:
        return yaml.load(fid, loader)
