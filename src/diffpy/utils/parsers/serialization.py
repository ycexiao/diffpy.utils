#!/usr/bin/env python
##############################################################################
#
# diffpy.utils      by DANSE Diffraction group
#                   Simon J. L. Billinge
#                   (c) 2010 The Trustees of Columbia University
#                   in the City of New York.  All rights reserved.
#
# File coded by:
#
# See AUTHORS.txt for a list of people who contributed.
# See LICENSE_DANSE.txt for license information.
#
##############################################################################

import json
import pathlib
import warnings

import numpy

from .custom_exceptions import ImproperSizeError, UnsupportedTypeError

# FIXME: add support for yaml, xml
supported_formats = [".json"]


def serialize_data(
    filename,
    hdata: dict,
    data_table,
    dt_colnames=None,
    show_path=True,
    serial_file=None,
):
    """Serialize file data into a dictionary. Can also save dictionary into a
    serial language file. Dictionary is formatted as {filename: data}.

    Requires hdata and data_table (can be generated by loadData).

    Parameters
    ----------
    filename
        Name of the file whose data is being serialized.
    hdata: dict
        File metadata (generally related to data table).
    data_table: list or ndarray
        Data table.
    dt_colnames: list
        Names of each column in data_table. Every name in data_table_cols
        will be put into the Dictionary as a key with a value of that column
        in data_table (stored as a List). Put None for columns without names.
        If dt_cols has less non-None entries than columns in data_table, the
        pair {'data table': data_table} will be put in the dictionary.
        (Default None: only entry {'data table': data_table} will be added to
        dictionary.)
    show_path: bool
        include a path element in the database entry (default True). If
        'path' is not included in hddata, extract path from filename.
    serial_file
        Serial language file to dump dictionary into. If None (default), no
        dumping will occur.

    Returns
    -------
    dict:
        Returns the dictionary loaded from/into the updated database file.
    """

    # compile data_table and hddata together
    data = {}

    # handle getting name of file for variety of filename types
    abs_path = pathlib.Path(filename).resolve()
    # add path to start of data if requested
    if show_path and "path" not in hdata.keys():
        data.update({"path": abs_path.as_posix()})
    # title the entry with name of file (taken from end of path)
    title = abs_path.name

    # first add data in hddata dict
    data.update(hdata)

    # second add named columns in dt_cols
    # performed second to prioritize overwriting hdata entries with data_
    # table column entries
    named_columns = 0  # initial value
    max_columns = 1  # higher than named_columns to trigger 'data table' entry
    if dt_colnames is not None:
        num_columns = [len(row) for row in data_table]
        max_columns = max(num_columns)
        num_col_names = len(dt_colnames)
        if (
            max_columns < num_col_names
        ):  # assume numpy.loadtxt gives non-irregular array
            raise ImproperSizeError(
                "More entries in dt_colnames than columns in data_table."
            )
        named_columns = 0
        for idx in range(num_col_names):
            colname = dt_colnames[idx]
            if colname is not None:
                if colname in hdata.keys():
                    warnings.warn(
                        (
                            f"Entry '{colname}' in hdata has been "
                            "overwritten by a data_table entry."
                        ),
                        RuntimeWarning,
                    )
                data.update({colname: list(data_table[:, idx])})
                named_columns += 1

    # finally add data_table as an entry named 'data table' if not all
    # columns were parsed
    if named_columns < max_columns:
        if "data table" in data.keys():
            warnings.warn(
                (
                    "Entry 'data table' in hdata has been "
                    "overwritten by data_table."
                ),
                RuntimeWarning,
            )
        data.update({"data table": data_table})

    # parse name using pathlib and generate dictionary entry
    entry = {title: data}

    # no save
    if serial_file is None:
        return entry

    # saving/updating file
    # check if supported type
    sf = pathlib.Path(serial_file)
    sf_name = sf.name
    extension = sf.suffix
    if extension not in supported_formats:
        raise UnsupportedTypeError(sf_name, supported_formats)

    # new file or update
    existing = False
    try:
        open(serial_file)
        existing = True
    except FileNotFoundError:
        pass

    # json
    if extension == ".json":
        # cannot serialize numpy arrays
        class NumpyEncoder(json.JSONEncoder):
            def default(self, data_obj):
                if type(data_obj) is numpy.ndarray:
                    return data_obj.tolist()
                return json.JSONEncoder.default(self, data_obj)

        # dump if non-existing
        if not existing:
            with open(serial_file, "w") as jsonfile:
                file_data = entry  # for return
                json.dump(file_data, jsonfile, indent=2, cls=NumpyEncoder)

        # update if existing
        else:
            with open(serial_file, "r") as json_read:
                file_data = json.load(json_read)
                file_data.update(entry)
            with open(serial_file, "w") as json_write:
                # dump to string first for formatting
                json.dump(file_data, json_write, indent=2, cls=NumpyEncoder)

    return file_data


def deserialize_data(filename, filetype=None):
    """Load a dictionary from a serial file.

    Parameters
    ----------
    filename
        Serial file to load from.

    filetype
        For specifying extension type (i.e. '.json').

    Returns
    -------
    dict
        A dictionary read from a serial file.
    """

    # check if supported type
    f = pathlib.Path(filename)
    f_name = f.name

    if filetype is None:
        extension = f.suffix
        if extension not in supported_formats:
            raise UnsupportedTypeError(f_name, supported_formats)
    else:
        extension = filetype

    return_dict = {}

    # json
    if extension == ".json":
        with open(filename, "r") as json_file:
            j_dict = json.load(json_file)
            return_dict = j_dict

    if len(return_dict) == 0:
        warnings.warn(
            "Loaded dictionary is empty. Possibly due to improper file type.",
            RuntimeWarning,
        )

    return return_dict
