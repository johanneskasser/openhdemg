"""
This module contains the functions that don't properly apply to the plot
or analysis category but that are necessary for the usability of the library.
The functions contained in this module can be considered as "tools" or
shortcuts necessary to operate with the HD-EMG recordings.
"""

import copy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from scipy.stats import iqr
from sklearn.svm import SVR
import warnings
from openhdemg.library.mathtools import compute_sil


def showselect(emgfile, how="ref_signal", title="", titlesize=12, nclic=2):
    """
    Visually select a part of the recording.

    The area can be selected based on the reference signal or based on the
    mean EMG signal. The selection can be performed with any letter or number
    in the keyboard, wrong points can be removed by pressing the right mouse
    button. Once finished, press enter to continue.

    This function does not check whether the selected points are within the
    effective file duration. This should be done based on user's need.

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile.
    how : str {"ref_signal", "mean_emg"}, default "ref_signal"
        What to display in the figure used to visually select the area to
        resize.

        ``ref_signal``
            Visualise the reference signal to select the area to resize.

        ``mean_emg``
            Visualise the mean EMG signal to select the area to resize.
    title : str
        The title of the plot. It is optional but strongly recommended.
        It should describe the task to do.
    titlesize : int, default 12
        The font size of the title.
    nclic: int, default 2
        The number of clics to be collected. If nclic < 1, all the clicks are
        collected.

    Returns
    -------
    points : list
        A list containing the selected points sorted in ascending order.

    Raises
    ------
    ValueError
        When the user clicked a wrong number of inputs in the GUI.

    Examples
    --------
    Load the EMG file and select the points based on the reference signal.

    >>> import openhdemg.library as emg
    >>> emgfile = emg.askopenfile(filesource="OTB_REFSIG")
    >>> points = emg.showselect(
    ...     emgfile,
    ...     how="ref_signal",
    ...     title="Select 2 points",
    ...     nclic=2,
    ... )
    >>> points
    [16115, 40473]

    Load the EMG file and select the points based on the mean EMG signal.

    >>> import openhdemg.library as emg
    >>> emgfile = emg.askopenfile(filesource="OPENHDEMG")
    >>> points = emg.showselect(
    ...     emgfile,
    ...     how="mean_emg",
    ...     title="Select 2 points",
    ...     nclic=2,
    ... )
    >>> points
    [135, 26598]
    """

    # Get the data to plot
    if how == "ref_signal":
        data_to_plot = emgfile["REF_SIGNAL"][0]
        y_label = "Reference signal"
    elif how == "mean_emg":
        data_to_plot = emgfile["RAW_SIGNAL"].mean(axis=1)
        y_label = "Mean EMG signal"
    else:
        raise ValueError(
            "Wrong argument in showselect(). how can only be 'ref_signal' or "
            + f"'mean_emg'. {how} was passed instead."
        )

    # Show the signal for the selection
    plt.figure()
    plt.plot(data_to_plot)
    plt.xlabel("Samples")
    plt.ylabel(y_label)
    plt.title(title, fontweight="bold", fontsize=titlesize)

    ginput_res = plt.ginput(n=-1, timeout=0, mouse_add=False, show_clicks=True)

    plt.close()

    points = [round(point[0]) for point in ginput_res]
    points.sort()

    if nclic > 0 and nclic != len(points):
        raise ValueError("Wrong number of inputs, read the title")

    return points


def create_binary_firings(emg_length, number_of_mus, mupulses):
    """
    Create a binary representation of the MU firing.

    Create a binary representation of the MU firing over time
    based on the times of firing of each MU.

    Parameters
    ----------
    emg_length : int
        Number of samples (length) in the emg file.
    number_of_mus : int
        Number of MUs in the emg file.
    mupulses : list of ndarrays
        Each ndarray should contain the times of firing (in samples) of each
        MU.

    Returns
    -------
    binary_MUs_firing : pd.DataFrame
        A pd.DataFrame containing the binary representation of MUs firing.
    """

    # Skip the step if I don't have the mupulses (is nan)
    if not isinstance(mupulses, list):
        raise ValueError("mupulses is not a list of ndarrays")

    # Initialise a pd.DataFrame with zeros
    binary_MUs_firing = pd.DataFrame(
        np.zeros((emg_length, number_of_mus), dtype=int)
    )

    for mu in range(number_of_mus):
        if len(mupulses[mu]) > 0:
            firing_points = mupulses[mu].astype(int)
            binary_MUs_firing.iloc[firing_points, mu] = 1

    return binary_MUs_firing


def mupulses_from_binary(binarymusfiring):
    """
    Extract the MUPULSES from the binary MUs firings.

    Parameters
    ----------
    binarymusfiring : pd.DataFrame
        A pd.DataFrame containing the binary representation of MUs firings.

    Returns
    -------
    MUPULSES : list
        A list of ndarrays containing the firing time (in samples) of each MU.
    """

    # Create empty list of lists to fill with ndarrays containing the MUPULSES
    # (point of firing)
    numberofMUs = len(binarymusfiring.columns)
    MUPULSES = [[] for _ in range(numberofMUs)]

    for mu in binarymusfiring:  # Loop all the MUs
        my_ndarray = []
        for idx, x in binarymusfiring[mu].items():  # Loop the MU firing times
            if x > 0:
                my_ndarray.append(idx)
                # Take the firing time and add it to the ndarray

        MUPULSES[mu] = np.array(my_ndarray)

    return MUPULSES


def resize_emgfile(
    emgfile,
    area=None,
    how="ref_signal",
    accuracy="recalculate",
    ignore_negative_ipts=False,
):
    """
    Resize all the components in the emgfile.

    This function can be useful to compute the various parameters only in the
    area of interest.

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile to resize.
    area : None or list, default None
        The resizing area. If already known, it can be passed in samples, as a
        list (e.g., [120,2560]).
        If None, the user can select the area of interest manually.
    how : str {"ref_signal", "mean_emg"}, default "ref_signal"
        If area==None, allow the user to visually select the area to resize
        based on how.

        ``ref_signal``
            Visualise the reference signal to select the area to resize.

        ``mean_emg``
            Visualise the mean EMG signal to select the area to resize.
    accuracy : str {"recalculate", "maintain"}, default "recalculate"

        ``recalculate``
            The Silhouette score is computed in the new resized file. This can
            be done only if IPTS is present.

        ``maintain``
            The original accuracy measure already contained in the emgfile is
            returned without any computation.
    ignore_negative_ipts : bool, default False
        This parameter determines the silhouette score estimation. If True,
        only positive ipts values are used during peak and noise clustering.
        This is particularly important for compensating sources with large
        negative components. This parameter is considered only if
        accuracy=="recalculate".

    Returns
    -------
    rs_emgfile : dict
        the new (resized) emgfile.
    start_, end_ : int
        the start and end of the selection (can be used for code automation).

    Notes
    -----
    Suggested names for the returned objects: rs_emgfile, start_, end_.

    Examples
    --------
    Manually select the area to resize the emgfile based on mean EMG signal
    and recalculate the silhouette score in the new portion of the signal.

    >>> emgfile = emg.askopenfile(filesource="DEMUSE", ignore_negative_ipts=True)
    >>> rs_emgfile, start_, end_ = emg.resize_emgfile(
    ...     emgfile,
    ...     how="mean_emg",
    ...     accuracy="recalculate",
    ... )

    Automatically resize the emgfile in the pre-specified area. Do not
    recalculate the silhouette score in the new portion of the signal.

    >>> emgfile = emg.askopenfile(filesource="CUSTOMCSV")
    >>> rs_emgfile, start_, end_ = emg.resize_emgfile(
    ...     emgfile,
    ...     area=[120, 25680],
    ...     accuracy="maintain",
    ... )
    """

    # Identify the area of interest
    if isinstance(area, list) and len(area) == 2:
        start_ = area[0]
        end_ = area[1]

    else:
        # Visualise and select the area to resize
        title = (
            "Select the start/end area to resize by hovering the mouse" +
            "\nand pressing the 'a'-key. Wrong points can be removed with " +
            "right \nclick or canc/delete key. When ready, press enter."
        )
        points = showselect(
            emgfile,
            how=how,
            title=title,
            titlesize=10,
        )
        start_, end_ = points[0], points[1]

    # Double check that start_, end_ are within the real range.
    if start_ < 0:
        start_ = 0
    # Continued inside if...

    # Create the object to store the resized emgfile.
    rs_emgfile = copy.deepcopy(emgfile)

    if emgfile["SOURCE"] in ["DEMUSE", "OTB", "CUSTOMCSV", "DELSYS"]:
        """
        ACCURACY should be re-computed on the new portion of the file if
        possible. Need to be resized: ==>
        emgfile =   {
            "SOURCE": SOURCE,
            ==> "RAW_SIGNAL": RAW_SIGNAL,
            ==> "REF_SIGNAL": REF_SIGNAL,
            ==> "ACCURACY": ACCURACY,
            ==> "IPTS": IPTS,
            ==> "MUPULSES": MUPULSES,
            "FSAMP": FSAMP,
            "IED": IED,
            ==> "EMG_LENGTH": EMG_LENGTH,
            "NUMBER_OF_MUS": NUMBER_OF_MUS,
            ==> "BINARY_MUS_FIRING": BINARY_MUS_FIRING,
        }
        """

        # Double check that start_, end_ are within the real range.
        if end_ > emgfile["RAW_SIGNAL"].shape[0]:
            end_ = emgfile["RAW_SIGNAL"].shape[0]

        # Resize the reference signal and identify the first value of the
        # index to resize the mupulses. Then, reset the index.
        rs_emgfile["REF_SIGNAL"] = rs_emgfile["REF_SIGNAL"].loc[start_:end_]
        rs_emgfile["REF_SIGNAL"] = rs_emgfile["REF_SIGNAL"].reset_index(drop=True)
        rs_emgfile["RAW_SIGNAL"] = rs_emgfile["RAW_SIGNAL"].loc[start_:end_]
        first_idx = rs_emgfile["RAW_SIGNAL"].index[0]
        rs_emgfile["RAW_SIGNAL"] = rs_emgfile["RAW_SIGNAL"].reset_index(drop=True)
        rs_emgfile["IPTS"] = rs_emgfile["IPTS"].loc[start_:end_].reset_index(drop=True)
        rs_emgfile["EMG_LENGTH"] = int(len(rs_emgfile["RAW_SIGNAL"].index))
        rs_emgfile["BINARY_MUS_FIRING"] = (
            rs_emgfile["BINARY_MUS_FIRING"].loc[start_:end_].reset_index(drop=True)
        )

        for mu in range(rs_emgfile["NUMBER_OF_MUS"]):
            # Mask the array based on a filter and return the values in an
            # array. However, make sure that all the numbers are int32 to
            # prevent falling to int16 when small sections are resized.
            # This may cause overflow.
            rs_emgfile["MUPULSES"][mu] = rs_emgfile["MUPULSES"][mu].astype(
                np.int32
            )

            rs_emgfile["MUPULSES"][mu] = (
                rs_emgfile["MUPULSES"][mu][
                    (rs_emgfile["MUPULSES"][mu] >= start_)
                    & (rs_emgfile["MUPULSES"][mu] < end_)
                ]
                - first_idx
            )

        # Compute SIL or leave original ACCURACY
        if accuracy == "recalculate":
            if rs_emgfile["NUMBER_OF_MUS"] > 0:
                if not rs_emgfile["IPTS"].empty:
                    # Calculate SIL
                    for mu in range(rs_emgfile["NUMBER_OF_MUS"]):
                        res = compute_sil(
                            ipts=rs_emgfile["IPTS"][mu],
                            mupulses=rs_emgfile["MUPULSES"][mu],
                            ignore_negative_ipts=ignore_negative_ipts,
                        )
                        rs_emgfile["ACCURACY"].iloc[mu] = res

                else:
                    raise ValueError(
                        "Impossible to calculate ACCURACY (SIL). IPTS not " +
                        "found. If IPTS is not present or empty, set " +
                        "accuracy='maintain'"
                    )

        elif accuracy == "maintain":
            # rs_emgfile["ACCURACY"] = rs_emgfile["ACCURACY"]
            pass

        else:
            raise ValueError(
                f"Accuracy can only be 'recalculate' or 'maintain'. {accuracy} was passed instead."
            )

        return rs_emgfile, start_, end_

    elif emgfile["SOURCE"] in ["OTB_REFSIG", "CUSTOMCSV_REFSIG", "DELSYS_REFSIG"]:
        # Double check that start_, end_ are within the real range.
        if end_ > emgfile["REF_SIGNAL"].shape[0]:
            end_ = emgfile["REF_SIGNAL"].shape[0]

        rs_emgfile["REF_SIGNAL"] = rs_emgfile["REF_SIGNAL"].loc[start_:end_]
        rs_emgfile["REF_SIGNAL"] = rs_emgfile["REF_SIGNAL"].reset_index(drop=True)

        return rs_emgfile, start_, end_

    else:
        raise ValueError("\nFile source not recognised\n")


class EMGFileSectionsIterator:
    """
    An iterator for splitting a file into sections and performing actions.

    This iterator can be used to split the emgfile (or emg_refsig file) in
    multiple sections, to apply specific funtions to each of these sections
    and to gather their results.

    This class has a number of methods that help in the splitting process,
    in the iteration of the various sections, and in merging the results.

    Parameters
    ----------
    file : dict
        The dictionary containing the emgfile (or emg_refsig file).

    Attributes
    ----------
    file : dict
        The dictionary containing the file to split and iterate.
    file_length : int
        The file duration in samples.
    split_points : list of int
        A list of sample indices where the file should be split into sections.
    sections : list
        A list of sections of the file, created based on split_points.
    results : list
        A list to store the results of operations applied to each section of
        the file.

    Methods
    -------
    set_split_points_by_showselect()
        Manually set the points used to split the emgfile.
    set_split_points_by_equal_spacing()
        Set the points used to split the emgfile into equal sections.
    set_split_points_by_time()
        Set the points used to split the emgfile based on a fixed time window.
    set_split_points_by_samples()
        Set the points used to split the emgfile based on a samples window.
    set_split_points_by_list()
        Set the points used to split the emgfile based on a provided list of
        sample indices.
    split()
        Splits the file into sections using the set split points.
    iterate()
        Apply a collection of functions to the split sections, each with its
        own arguments.
    merge_dataframes()
        Merge a list of result DataFrames using the specified method.
    """

    def __init__(self, file):
        # Initializes the iterator for an emgfile.

        self.file = file
        self.split_points = []
        self.sections = []
        self.results = []
        self.file_length = 0

        # Get file duration based on wether we have an emgfile or an
        # emg_refsig file.
        if "EMG_LENGTH" in self.file:  # Standard emgfile
            self.file_length = self.file["EMG_LENGTH"]
        elif "RAW_SIGNAL" in self.file:  # Fallback
            self.file_length = self.file["RAW_SIGNAL"].shape[0]
        elif "REF_SIGNAL" in self.file:  # Standard emg_refsig
            self.file_length = self.file["REF_SIGNAL"].shape[0]
        else:
            raise ValueError(
                "Impossible to determine file length. None of EMG_LENGTH, " +
                "RAW_SIGNAL and REF_SIGNAL are available in the file."
            )
        self.file_length = int(self.file_length)

    def set_split_points_by_showselect(
        self,
        how="ref_signal",
        title="",
        titlesize=10,
        nclic=-1,
    ):
        """
        Manually set the points used to split the emgfile.

        Calls the emg.showselect() function to manually select the split points
        based on the visualisation of the reference signal or of the EMG
        signal amplitude.

        Points can be added by pressing keyboard letters while hovering over
        the point to resize. Right mouse click removes the point. Press 'enter'
        to confirm the selection. Sections are cut starting from the first
        point and then on the consecutove points.

        Parameters
        ----------
        how : str {"ref_signal", "mean_emg"}, default "ref_signal"
            What to display in the figure used to visually select the area to
            resize.

            ``ref_signal``
                Visualise the reference signal to select the area to resize.

            ``mean_emg``
                Visualise the mean EMG signal to select the area to resize.
        title : str
            The title of the plot. It is optional but strongly recommended.
            It should describe the task to do. A default title is provided when
            title="".
        titlesize : int, default 12
            The font size of the title.
        nclic: int, default -1
            The number of clics to be collected. If nclic < 1, all the clicks
            are collected.

        Returns
        -------
        None
            Stores the split points in `self.split_points`.

        Raises
        ------
        ValueError
            When the user clicked a wrong number of inputs in the GUI.

        Examples
        --------
        Manually set the points to resize the file by visualising the reference
        signal.

        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_showselect(how="ref_signal")
        >>> split_points = iterator.split_points
        >>> split_points
        [0, 6562, 19552, 41546, 55273, 62802]

        Manually set the points to resize the file by visualising the mean
        EMG signal amplitude.

        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_showselect(how="mean_emg")
        >>> split_points = iterator.split_points
        >>> split_points
        [5381, 23094, 38889, 50107]
        """

        # Fallback title
        if len(title) == 0:
            title = (
                "Select the points where to resize by hovering the mouse" +
                "\nand pressing the 'a'-key. Wrong points can be removed " +
                "with right\nclick or canc/delete keys. When ready, press " +
                "enter."
            )

        split_points = showselect(
            emgfile=self.file, how=how, title=title, titlesize=titlesize,
            nclic=nclic,
        )

        # Double check that split_points are within the real range.
        points_below = [x for x in split_points if x < 0]
        if len(points_below) > 1:
            raise ValueError(
                "More than 1 point has been selected below 0."
            )
        elif len(points_below) == 1:
            if split_points[0] < 0:
                split_points[0] = 0
            else:
                raise ValueError(
                    "There are points below 0 different from the firt " +
                    "element of the list, check points beeing sorted."
                )

        points_above = [x for x in split_points if x > self.file_length]
        if len(points_above) > 1:
            raise ValueError(
                "More than 1 point has been selected after the end of the " +
                "signal."
            )
        elif len(points_above) == 1:
            if split_points[-1] > self.file_length:
                split_points[-1] = self.file_length
            else:
                raise ValueError(
                    "There are points after the end of the file different " +
                    "from the firt element of the list, check points beeing " +
                    "sorted."
                )

        self.split_points = split_points

    def set_split_points_by_equal_spacing(self, n_sections):
        """
        Set the points used to split the emgfile into equal sections.

        All the sections will have approximately the same length (length
        rounding may apply), which is calculated based on n_sections.

        Parameters
        ----------
        n_sections : int
            The number of sections to divide the emgfile into.

        Returns
        -------
        None
            Stores the split points in `self.split_points`.

        Examples
        --------
        Divide the file in 3 sections of the same length.

        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_equal_spacing(n_sections=3)
        >>> split_points = iterator.split_points
        >>> split_points
        [0, 22186, 44373, 66560]
        """

        space = self.file_length
        self.split_points = list(
            np.linspace(0, space, n_sections + 1, dtype=int)
        )

    def set_split_points_by_time(self, time_window, drop_shorter=False):
        """
        Set the points used to split the emgfile based on a fixed time window.


        Parameters
        ----------
        time_window : float
            The duration of each section in seconds.
        drop_shorter : bool, default False
            If True, the last section is discarded if it is shorter than
            `time_window`. If False, the last section will include the
            remaining samples even if it is shorter than `time_window`.

        Returns
        -------
        None
            Stores the split points in `self.split_points`.

        Examples
        --------
        Divide the file into consecutive 9-second sections, with any remaining
        data forming a final shorter section.

        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_time(
        ...     time_window=9,
        ...     drop_shorter=False,
        ... )
        >>> split_points = iterator.split_points
        >>> split_points
        [0, 18432, 36864, 55296, 66560]

        Divide the file into consecutive 9-second sections, discarding any
        remaining data if it is shorter than the specified duration.

        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_time(
        ...     time_window=9,
        ...     drop_shorter=True,
        ... )
        >>> split_points = iterator.split_points
        >>> split_points
        [0, 18432, 36864, 55296]
        """

        fsamp = self.file["FSAMP"]
        space = self.file_length

        step = int(round(time_window * fsamp))
        self.split_points = list(range(0, space + 1, step))

        # Append the last point if it's missing and drop_shorter is False
        if self.split_points[-1] != space:
            if not drop_shorter:
                self.split_points.append(space)

    def set_split_points_by_samples(self, samples_window, drop_shorter=False):
        """
        Set the points used to split the emgfile based on a samples window.

        Parameters
        ----------
        samples_window : int
            The duration of each section in samples.
        drop_shorter : bool, default False
            If True, the last section is discarded if it is shorter than
            `samples_window`. If False, the last section will include the
            remaining samples even if it is shorter than `samples_window`.

        Returns
        -------
        None
            Stores the split points in `self.split_points`.

        Examples
        --------
        Divide the file into consecutive 9-second sections, with any remaining
        data forming a final shorter section.

        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_samples(
        ...     samples_window=10000,
        ...     drop_shorter=False,
        ... )
        >>> split_points = iterator.split_points
        >>> split_points
        [0, 10000, 20000, 30000, 40000, 50000, 60000, 66560]

        Divide the file into consecutive 9-second sections, discarding any
        remaining data if it is shorter than the specified duration.

        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_samples(
        ...     samples_window=10000,
        ...     drop_shorter=True,
        ... )
        >>> split_points = iterator.split_points
        >>> split_points
        [0, 10000, 20000, 30000, 40000, 50000, 60000]
        """

        space = self.file_length
        step = samples_window
        self.split_points = list(range(0, space + 1, step))

        # Append the last point if it's missing and drop_shorter is False
        if self.split_points[-1] != space:
            if not drop_shorter:
                self.split_points.append(space)

    def set_split_points_by_list(self, split_points):
        """
        Set the points used to split the emgfile based on a provided list of
        sample indices.

        Parameters
        ----------
        split_points : list of int
            A list containing the sample indices at which to split the emgfile.
            These indices should correspond to the points where the data will
            be divided into sections.

        Returns
        -------
        None
            Stores the split points in `self.split_points`.

        Examples
        --------
        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_list(split_points=[0, 18432, 36864])
        >>> split_points = iterator.split_points
        >>> split_points
        [0, 18432, 36864]
        """

        self.split_points = split_points

    def split(self, accuracy="recalculate", ignore_negative_ipts=False):
        """
        Splits the file into sections using the set split points.

        Parameters
        ----------
        accuracy : str {"recalculate", "maintain"}, default "recalculate"

            ``recalculate``
                The Silhouette score is computed in the new resized file. This
                can be done only if IPTS is present.

            ``maintain``
                The original accuracy measure already contained in the emgfile
                is returned without any computation.
        ignore_negative_ipts : bool, default False
            This parameter determines the silhouette score estimation. If True,
            only positive ipts values are used during peak-noise clustering.
            This is particularly important for compensating sources with large
            negative components. This parameter is considered only if
            accuracy=="recalculate".

        Returns
        -------
        None
            Stores the split sections in `self.sections`.

        Examples
        --------
        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_equal_spacing(n_sections=4)
        >>> iterator.split()
        >>> sections = iterator.sections
        >>> len(sections)
        4
        """

        self.sections = []
        for start, end in zip(self.split_points[:-1], self.split_points[1:]):
            rs_emgfile, _, _ = resize_emgfile(
                self.file, area=[start, end],
                accuracy=accuracy,
                ignore_negative_ipts=ignore_negative_ipts,
            )
            self.sections.append(rs_emgfile)

    def iterate(self, funcs=[], args_list=[[]], kwargs_list=[{}], **kwargs):
        """
        Apply a collection of functions to the split sections, each with its
        own arguments.

        Parameters
        ----------
        funcs : list of callables
            A list of functions to apply to each section. If multiple functions
            are provided, their count must match the number of sections. If
            only one function is given, it will be applied to all sections.
            IMPORTANT! Each function must take `file` as the first parameter.
        args_list : list of lists
            A list where each element is a list of positional arguments to be
            passed to the corresponding function in `funcs`. Must have the same
            length as `funcs`.
        kwargs_list : list of dicts, optional
            A list where each element is a dictionary of keyword arguments to
            be passed to the corresponding function in `funcs`. Must have the
            same length as `funcs`.
        **kwargs
            Additional keyword arguments that are passed to all functions in
            `funcs`. If `funcs` contains only 1 function, **kwargs can be used
            instead of kwargs_list for simpler syntax.

        Returns
        -------
        None
            Stores the results in `self.results`, where each function's output
            is collected.

        Examples
        --------
        Split the file in 3 sections and apply a custom function to each
        section to count the number of firings in each MU. Then visualise the
        results for the first section.

        >>> import openhdemg.library as emg
        >>> import pandas as pd
        >>> def count_firings(emgfile):
        ...     res = [len(mu_firings) for mu_firings in emgfile["MUPULSES"]]
        ...     return pd.DataFrame(res)
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_equal_spacing(n_sections=3)
        >>> iterator.split()
        >>> iterator.iterate(funcs=[count_firings])
        >>> results = iterator.results
        >>> results[0]
            0
        0  48
        1  43
        2  63
        3  94
        4  95

        Split the file in 3 sections and calculate the discharge rate of each
        MU over the first 20 discharges.

        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_equal_spacing(n_sections=3)
        >>> iterator.split()
        >>> iterator.iterate(
        ...     funcs=[emg.compute_dr],
        ...     event_="rec",
        ...     n_firings_RecDerec=20,
        ... )
        >>> results = iterator.results
        >>> results[0]
             DR_rec     DR_all
        0  7.468962   7.714276
        1  7.091045   7.390155
        2  7.673784   8.583193
        3  9.004878  11.042002
        4  9.705901  11.202489
        """

        # Extensive input checking to help using the iterate function.
        if not isinstance(funcs, list):
            raise ValueError("Funcs must be a list")
        if not isinstance(args_list, list):
            raise ValueError("args_list must be a list")
        if not isinstance(kwargs_list, list):
            raise ValueError("kwargs_list must be a list")

        # Manage multiple functions
        if len(funcs) > 1:
            if len(funcs) != len(self.sections):
                raise ValueError(
                    "funcs must be a list containing 1 function to be " +
                    "applied to all the sections or 1 function for each " +
                    "section."
                )
            if len(args_list) > 0:
                if not isinstance(args_list[0], list):
                    raise ValueError(
                        "args_list must be a list containing 1 list of " +
                        "arguments for each function."
                    )
                if len(args_list) != len(self.sections):
                    raise ValueError(
                        "args_list must be a list containing 1 list of " +
                        "arguments for each function."
                    )
            if len(kwargs_list) > 0:
                if not isinstance(kwargs_list[0], dict):
                    raise ValueError(
                        "kwargs_list must be a list containing 1 dict of " +
                        "keyword arguments for each function."
                    )
                if len(kwargs_list) != len(self.sections):
                    raise ValueError(
                        "kwargs_list must be a list containing 1 dict of " +
                        "keyword arguments for each function."
                    )

        elif len(funcs) == 1:
            if len(args_list) == 1:
                if not isinstance(args_list[0], list):
                    raise ValueError(
                        "args_list must be a list containing 1 list of " +
                        "arguments for each function."
                    )
            elif len(args_list) > 1:
                raise ValueError(
                    "args_list must be a list containing 1 list of " +
                    "arguments for each function."
                )

            if len(kwargs_list) == 1:
                if not isinstance(kwargs_list[0], dict):
                    raise ValueError(
                        "kwargs_list must be a list containing 1 dict of " +
                        "keyword arguments for each function."
                    )
            elif len(kwargs_list) > 1:
                raise ValueError(
                    "kwargs_list must be a list containing 1 dict of " +
                    "keyword arguments for each function."
                )

        else:
            raise ValueError("No function provided to iterate")

        # Proagate single function to fit the number of sections
        if len(funcs) == 1 and len(self.sections) > 1:
            funcs = [funcs[0] for _ in self.sections]
            args_list = [args_list[0] for _ in self.sections]
            kwargs_list = [kwargs_list[0] for _ in self.sections]

        # Calculate the results for each section
        for idx, section in enumerate(self.sections):
            func = funcs[idx]
            func_args = args_list[idx]
            func_kwargs = kwargs_list[idx]
            combined_kwargs = {**func_kwargs, **kwargs}
            result = func(section, *func_args, **combined_kwargs)
            self.results.append(result)

    def merge_dataframes(self, method="long", fillna=None, agg_func=None):
        """
        Merge a list of result DataFrames using the specified method.

        Parameters
        ----------
        method : str, default "long"
            The merging method. When using built-in methods (except for
            `custom`), all DataFrames must have the same structure (i.e.,
            aligned columns and index).

            ``average``
                Computes the mean across all DataFrames.

            ``median``
                Computes the median across all DataFrames.

            ``sum``
                Computes the sum across all DataFrames.

            ``min``
                Takes the minimum value across all DataFrames.

            ``max``
                Takes the maximum value across all DataFrames.

            ``std``
                Computes the standard deviation across all DataFrames.

            ``cv``
                Computes the coefficient of variation (CV = std / mean).

            ``long``
                Stacks all DataFrames with an additional 'source_idx' column.

            ``custom``
                Uses a user-defined aggregation function provided via
                `agg_func`.
        fillna : float or None
            If specified, fills missing values (NaN) with this value before
            merging.
        agg_func : callable or None
            A custom aggregation function to apply when method="custom". The
            function should take a list of DataFrames and return a single
            DataFrame.

        Returns
        -------
        merged_df : pd.DataFrame
            The merged DataFrame.

        Raises
        ------
        ValueError
            If `self.results` is empty or contains non-DataFrame elements;
            or, `method` is unknown; or `agg_func` is missing when
            method="custom".

        Examples
        --------
        Merge all the results in a long format DataFrame. Best for statistical
        analyses.

        >>> import openhdemg.library as emg
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_equal_spacing(n_sections=3)
        >>> iterator.split()
        >>> iterator.iterate(funcs=[emg.compute_dr], event_="rec")
        >>> merged_results = iterator.merge_dataframes()
        >>> merged_results
            source_idx  original_idx     DR_rec     DR_all
        0            0             0   3.341579   7.714276
        1            0             1   5.701081   7.390155
        2            0             2   5.699017   8.583193
        3            0             3   7.548770  11.042002
        4            0             4   8.344515  11.202489
        5            1             0  10.235710   8.155868
        6            1             1   6.769358   6.758350
        7            1             2   8.193645   8.054868
        8            1             3  10.952495  11.151536
        9            1             4  11.012249  10.691432
        10           2             0   6.430406   6.899233
        11           2             1   6.714442   6.274404
        12           2             2   7.057244   6.881602
        13           2             3  10.577538   9.578987
        14           2             4   9.708064   9.562182

        Apply a custom function to each section to count the number of firings
        in each MU, then get the mean and STD values across the 3 sections
        (just for didactical purposes).

        >>> import openhdemg.library as emg
        >>> import pandas as pd
        >>> def count_firings(emgfile):
        ...     res = [len(mu_firings) for mu_firings in emgfile["MUPULSES"]]
        ...     return pd.DataFrame(res)
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_equal_spacing(n_sections=3)
        >>> iterator.split()
        >>> iterator.iterate(funcs=[count_firings])
        >>> mean_values = iterator.merge_dataframes(
        ...     method="average",
        ...     fillna=0,
        ... )
        >>> std_values = iterator.merge_dataframes(
        ...     method="std",
        ...     fillna=0,
        ... )
        >>> mean_values
                   0
        0  45.666667
        1  51.333333
        2  65.666667
        3  97.666667
        4  97.333333
        >>> std_values
                   0
        0   4.932883
        1  18.009257
        2  20.132892
        3  20.744477
        4  16.623277

        Apply a custom method by providing an external aggregation function
        which finds the maximum value at each position and the index of the
        DataFrame containing it.

        >>> import openhdemg.library as emg
        >>> import pandas as pd
        >>> def max_with_source(results_dataframes):
        ...     stacked = pd.concat(
        ...         results_dataframes, keys=range(len(results_dataframes))
        ...     )
        ...     max_values = stacked.groupby(level=1).max()
        ...     max_indices = stacked.groupby(level=1).idxmax().iloc[:, 0]
        ...     max_values["source_idx"] = max_indices.map(lambda x: x[0])
        ...     return max_values
        >>> emgfile = emg.emg_from_samplefile()
        >>> iterator = emg.EMGFileSectionsIterator(file=emgfile)
        >>> iterator.set_split_points_by_equal_spacing(n_sections=3)
        >>> iterator.split()
        >>> iterator.iterate(funcs=[emg.compute_dr], event_="rec")
        >>> max_values_with_source = iterator.merge_dataframes(
        ...     method="custom",
        ...     fillna=0,
        ...     agg_func=max_with_source,
        ... )
        >>> max_values_with_source
              DR_rec     DR_all  source_idx
        0  10.235710   8.155868           1
        1   6.769358   7.390155           1
        2   8.193645   8.583193           1
        3  10.952495  11.151536           1
        4  11.012249  11.202489           1
        """

        if not self.results:
            raise ValueError("The list of dataframes is empty.")

        if not all(isinstance(df, pd.DataFrame) for df in self.results):
            raise ValueError(
                "All elements in `self.results` must be pd.DataFrames."
            )

        # Optionally fill NaN values
        if fillna is not None:
            self.results = [df.fillna(fillna) for df in self.results]

        # Stack DataFrames along axis=0 for operations like std and cv
        merged_stack = pd.concat(
            self.results, axis=0, keys=range(len(self.results)),
        )

        if method == "average":
            merged_df = merged_stack.groupby(level=1).mean()

        elif method == "median":
            merged_df = merged_stack.groupby(level=1).median()

        elif method == "sum":
            merged_df = merged_stack.groupby(level=1).sum()

        elif method == "min":
            merged_df = merged_stack.groupby(level=1).min()

        elif method == "max":
            merged_df = merged_stack.groupby(level=1).max()

        elif method == "std":
            merged_df = merged_stack.groupby(level=1).std()

        elif method == "cv":
            mean_df = merged_stack.groupby(level=1).mean()
            std_df = merged_stack.groupby(level=1).std()
            merged_df = std_df / mean_df

        elif method == "long":
            # Preserve original index (often indicating the MU number) by
            # renaming it to 'original_idx', and assign source index to detect
            # from which DataFrame the results come from.
            merged_df = pd.concat(
                [
                    df.reset_index().rename(
                        columns={"index": "original_idx"}
                    ).assign(source_idx=i)
                    for i, df in enumerate(self.results)
                ],
                ignore_index=True
            )

            # Ensure consistent column order
            cols = ["source_idx", "original_idx"] + [
                col for col in merged_df.columns if col not in [
                    "source_idx", "original_idx"
                ]
            ]
            merged_df = merged_df[cols]

        elif method == "custom":
            if agg_func is None:
                raise ValueError(
                    "When using method='custom', `agg_func` must be provided."
                )
            merged_df = agg_func(self.results)

        else:
            raise ValueError(f"Unknown method '{method}'")

        return merged_df


def compute_idr(emgfile):
    """
    Compute the IDR.

    This function computes the instantaneous discharge rate (IDR) from the
    MUPULSES.
    The IDR is very useful for plotting and visualisation of the MUs behaviour.

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile.

    Returns
    -------
    idr : dict
        A dict containing a pd.DataFrame for each MU (keys are integers).
        Accessing the key, we have a pd.DataFrame containing:

        - mupulses: firing sample.
        - diff_mupulses: delta between consecutive firing samples.
        - timesec: delta between consecutive firing samples in seconds.
        - idr: instantaneous discharge rate.

    Examples
    --------
    Load the EMG file, compute IDR and access the results for the first MU.

    >>> import openhdemg.library as emg
    >>> emgfile = emg.askopenfile(filesource="OTB", otb_ext_factor=8)
    >>> idr = emg.compute_idr(emgfile=emgfile)
    >>> munumber = 0
    >>> idr[munumber]
        mupulses  diff_mupulses    timesec       idr
    0        9221            NaN   4.502441       NaN
    1        9580          359.0   4.677734  5.704735
    2        9973          393.0   4.869629  5.211196
    3       10304          331.0   5.031250  6.187311
    4       10617          313.0   5.184082  6.543131
    ..        ...            ...        ...       ...
    149     54521          395.0  26.621582  5.184810
    150     54838          317.0  26.776367  6.460568
    151     55417          579.0  27.059082  3.537133
    152     55830          413.0  27.260742  4.958838
    153     56203          373.0  27.442871  5.490617
    """

    # Compute the instantaneous discharge rate (IDR) from the MUPULSES
    if isinstance(emgfile["MUPULSES"], list):
        # Empty dict to fill with dataframes containing the MUPULSES
        # information
        idr = {x: np.nan**2 for x in range(emgfile["NUMBER_OF_MUS"])}

        for mu in range(emgfile["NUMBER_OF_MUS"]):
            # Manage the exception of a single MU and add MUPULSES in column 0
            df = pd.DataFrame(
                emgfile["MUPULSES"][mu]
                if emgfile["NUMBER_OF_MUS"] > 1
                else np.transpose(np.array(emgfile["MUPULSES"]))
            )

            # Calculate difference in MUPULSES and add it in column 1
            df[1] = df[0].diff()
            # Calculate time in seconds and add it in column 2
            df[2] = df[0] / emgfile["FSAMP"]
            # Calculate the idr and add it in column 3
            df[3] = emgfile["FSAMP"] / df[1]

            df = df.rename(
                columns={
                    0: "mupulses",
                    1: "diff_mupulses",
                    2: "timesec",
                    3: "idr",
                },
            )

            # Add the idr to the idr dict
            idr[mu] = df

        return idr

    else:
        raise Exception(
            "MUPULSES is probably absent or it is not contained in a list"
        )


def delete_mus(
    emgfile, munumber, if_single_mu="ignore", delete_delsys_muaps=True,
):
    """
    Delete unwanted MUs.

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile.
    munumber : int, list of int
        The MUs to remove. If a single MU has to be removed, this should be an
        int (number of the MU).
        If multiple MUs have to be removed, a list of int should be passed.
        An unpacked (*) range can also be passed as munumber=[*range(0, 5)].
        munumber is expected to be with base 0 (i.e., the first MU in the file
        is the number 0).
    if_single_mu : str {"ignore", "remove"}, default "ignore"
        A string indicating how to behave in case of a file with a single MU.

        ``ignore``
        Ignore the process and return the original emgfile. (Default)

        ``remove``
        Remove the MU and return the emgfile without the MU.
        This should allow full compatibility with the use of this file
        in following processing (i.e., save/load and analyse).
    delete_delsys_muaps : Bool, default True
        If true, deletes also the associated MUAPs computed by the Delsys
        software stored in emgfile["EXTRAS"].

    Returns
    -------
    emgfile : dict
        The dictionary containing the emgfile without the unwanted MUs.

    Examples
    --------
    Delete MUs 1,4,5 from the emgfile.

    >>> import openhdemg.library as emg
    >>> emgfile = emg.askopenfile(filesource="OTB", otb_ext_factor=8)
    >>> emgfile = emg.delete_mus(emgfile=emgfile, munumber=[1,4,5])
    """

    # Check how to behave in case of a single MU
    if if_single_mu == "ignore":
        # Check how many MUs we have, if we only have 1 MU, the entire file
        # should be deleted instead.
        if emgfile["NUMBER_OF_MUS"] <= 1:
            warnings.warn(
                "There is only 1 MU in the file, and it has not been removed. You can change this behaviour with if_single_mu='remove'"
            )

            return emgfile

    elif if_single_mu == "remove":
        pass

    else:
        raise ValueError(
            "if_single_mu must be one of 'ignore' or 'remove', {} was passed instead".format(
                if_single_mu
            )
        )

    # Create the object to store the new emgfile without the specified MUs.
    del_emgfile = copy.deepcopy(emgfile)
    """
    Need to be changed: ==>
    emgfile =   {
        "SOURCE" : SOURCE,
        "RAW_SIGNAL" : RAW_SIGNAL,
        "REF_SIGNAL" : REF_SIGNAL,
        ==> "ACCURACY" : ACCURACY
        ==> "IPTS" : IPTS,
        ==> "MUPULSES" : MUPULSES,
        "FSAMP" : FSAMP,
        "IED" : IED,
        "EMG_LENGTH" : EMG_LENGTH,
        ==> "NUMBER_OF_MUS" : NUMBER_OF_MUS,
        ==> "BINARY_MUS_FIRING" : BINARY_MUS_FIRING,
        ==> "EXTRAS" : EXTRAS but only for DELSYS file
    }
    """

    # Common part working for all the possible inputs to munumber
    # Drop ACCURACY values and reset the index
    del_emgfile["ACCURACY"] = del_emgfile["ACCURACY"].drop(munumber)
    # .drop() Works with lists and integers
    del_emgfile["ACCURACY"] = del_emgfile["ACCURACY"].reset_index(drop=True)

    # Drop IPTS by columns and rename the columns
    del_emgfile["IPTS"] = del_emgfile["IPTS"].drop(munumber, axis=1)
    del_emgfile["IPTS"].columns = range(del_emgfile["IPTS"].shape[1])

    # Drop BINARY_MUS_FIRING by columns and rename the columns
    del_emgfile["BINARY_MUS_FIRING"] = del_emgfile["BINARY_MUS_FIRING"].drop(
        munumber, axis=1
    )
    del_emgfile["BINARY_MUS_FIRING"].columns = range(
        del_emgfile["BINARY_MUS_FIRING"].shape[1]
    )

    if isinstance(munumber, int):
        # Delete MUPULSES by position in the list.
        del del_emgfile["MUPULSES"][munumber]

        # Subrtact one MU to the total number
        del_emgfile["NUMBER_OF_MUS"] = del_emgfile["NUMBER_OF_MUS"] - 1

    elif isinstance(munumber, list):
        # Delete all the content in the del_emgfile["MUPULSES"] and append
        # only the MUs that we want to retain (exclude deleted MUs).
        # This is a workaround to directly deleting, for safer implementation.
        del_emgfile["MUPULSES"] = []
        for mu in range(emgfile["NUMBER_OF_MUS"]):
            if mu not in munumber:
                del_emgfile["MUPULSES"].append(emgfile["MUPULSES"][mu])

        # Subrtact the number of deleted MUs to the total number
        del_emgfile["NUMBER_OF_MUS"] = del_emgfile["NUMBER_OF_MUS"] - len(munumber)

    else:
        raise Exception(
            "While calling the delete_mus function, you should pass an integer or a list to munumber= "
        )

    # Verify if all the MUs have been removed. In that case, restore column
    # names in empty pd.DataFrames.
    if del_emgfile["NUMBER_OF_MUS"] == 0:
        # pd.DataFrame
        del_emgfile["IPTS"] = pd.DataFrame(columns=[0])
        del_emgfile["BINARY_MUS_FIRING"] = pd.DataFrame(columns=[0])
        # list of ndarray
        del_emgfile["MUPULSES"] = [np.array([])]

    if emgfile["SOURCE"] == "DELSYS" and delete_delsys_muaps:
        # Remove also DELSYS MUAPs
        if isinstance(munumber, int):
            munumber = [munumber]

        data = del_emgfile["EXTRAS"]

        for mu in munumber:
            # Get MU ID
            mu_id = f"MU_{mu}_"
            # Remove all columns with MU ID
            data = data[[col for col in data.columns if not col.startswith(mu_id)]]

        # Rescale the numbers in the remaining column names
        col_list = list(data.columns)
        if len(col_list) % 4 != 0:
            raise ValueError("Unexpected number of channels in Delsys MUAPS")
        new_col_list = []
        for mu in range(del_emgfile["NUMBER_OF_MUS"]):
            new_col_list.extend(
                [
                    f"MU_{mu}_CH_0",
                    f"MU_{mu}_CH_1",
                    f"MU_{mu}_CH_2",
                    f"MU_{mu}_CH_3",
                ]
            )
        data.columns = new_col_list

        del_emgfile["EXTRAS"] = data

    return del_emgfile


def delete_empty_mus(emgfile):
    """
    Delete all the MUs without firings.

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile.

    Returns
    -------
    emgfile : dict
        The dictionary containing the emgfile without the empty MUs.
    """

    # Find the index of empty MUs
    ind = []
    for i, mu in enumerate(range(emgfile["NUMBER_OF_MUS"])):
        if len(emgfile["MUPULSES"][mu]) == 0:
            ind.append(i)

    emgfile = delete_mus(emgfile, munumber=ind, if_single_mu="remove")

    return emgfile


def sort_mus(emgfile):
    """
    Sort the MUs in order of recruitment.

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile.

    Returns
    -------
    sorted_emgfile : dict
        The dictionary containing the sorted emgfile.
    """

    # If we only have 1 MU, there is no necessity to sort it.
    if emgfile["NUMBER_OF_MUS"] <= 1:
        return emgfile

    # Create the object to store the sorted emgfile.
    # Create a deepcopy to avoid changing the original emgfile
    sorted_emgfile = copy.deepcopy(emgfile)
    """
    Need to be changed: ==>
    emgfile =   {
                "SOURCE" : SOURCE,
                "RAW_SIGNAL" : RAW_SIGNAL,
                "REF_SIGNAL" : REF_SIGNAL,
                ==> "ACCURACY": ACCURACY,
                ==> "IPTS" : IPTS,
                ==> "MUPULSES" : MUPULSES,
                "FSAMP" : FSAMP,
                "IED" : IED,
                "EMG_LENGTH" : EMG_LENGTH,
                "NUMBER_OF_MUS" : NUMBER_OF_MUS,
                ==> "BINARY_MUS_FIRING" : BINARY_MUS_FIRING,
                }
    """

    # Identify the sorting_order by the first MUpulse of every MUs
    df = []
    for mu in range(emgfile["NUMBER_OF_MUS"]):
        if len(emgfile["MUPULSES"][mu]) > 0:
            df.append(emgfile["MUPULSES"][mu][0])
        else:
            df.append(np.inf)

    df = pd.DataFrame(df, columns=["firstpulses"])
    df.sort_values(by="firstpulses", inplace=True)
    sorting_order = list(df.index)

    # Sort ACCURACY (single column)
    for origpos, newpos in enumerate(sorting_order):
        sorted_emgfile["ACCURACY"].loc[origpos] = emgfile["ACCURACY"].loc[newpos]

    # Sort IPTS (multiple columns, sort by columns, then reset columns' name)
    sorted_emgfile["IPTS"] = sorted_emgfile["IPTS"].reindex(columns=sorting_order)
    sorted_emgfile["IPTS"].columns = np.arange(emgfile["NUMBER_OF_MUS"])

    # Sort BINARY_MUS_FIRING (multiple columns, sort by columns,
    # then reset columns' name)
    sorted_emgfile["BINARY_MUS_FIRING"] = sorted_emgfile["BINARY_MUS_FIRING"].reindex(
        columns=sorting_order
    )
    sorted_emgfile["BINARY_MUS_FIRING"].columns = np.arange(emgfile["NUMBER_OF_MUS"])

    # Sort MUPULSES.
    # Preferable to use the sorting_order as a double-check in alternative to:
    # sorted_emgfile["MUPULSES"] = sorted(
    #   sorted_emgfile["MUPULSES"], key=min, reverse=False)
    # )
    for origpos, newpos in enumerate(sorting_order):
        sorted_emgfile["MUPULSES"][origpos] = emgfile["MUPULSES"][newpos]

    return sorted_emgfile


def compute_covsteady(emgfile, start_steady=-1, end_steady=-1):
    """
    Calculates the covsteady.

    This function calculates the coefficient of variation of the steady-state
    phase (covsteady of the REF_SIGNAL).

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile.
    start_steady, end_steady : int, default -1
        The start and end point (in samples) of the steady-state phase.
        If < 0 (default), the user will need to manually select the start and
        end of the steady-state phase.

    Returns
    -------
    covsteady : float
        The coefficient of variation of the steady-state phase in %.

    See also
    --------
    - compute_idr : computes the instantaneous discharge rate.

    Examples
    --------
    Load the EMG file, compute covsteady and access the result from GUI.

    >>> import openhdemg.library as emg
    >>> emgfile = emg.askopenfile(filesource="OTB", otb_ext_factor=8)
    >>> covsteady = emg.compute_covsteady(emgfile=emgfile)
    >>> covsteady
    1.452806

    The process can be automated by bypassing the GUI.

    >>> import openhdemg.library as emg
    >>> emgfile = emg.askopenfile(filesource="OTB", otb_ext_factor=8)
    >>> covsteady = emg.compute_covsteady(
    ...     emgfile=emgfile,
    ...     start_steady=3580,
    ...     end_steady=15820,
    ... )
    >>> covsteady
    35.611263
    """

    if (start_steady < 0 and end_steady < 0) or (start_steady < 0 or end_steady < 0):
        title = (
            "Select the start/end area of the steady-state by hovering the " +
            "mouse \nand pressing the 'a'-key. Wrong points can be removed " +
            "with right \nclick or canc/delete key. When ready, press enter."
        )
        points = showselect(
            emgfile=emgfile,
            title=title,
            titlesize=10,
        )
        start_steady, end_steady = points[0], points[1]

    ref = emgfile["REF_SIGNAL"].loc[start_steady:end_steady]
    covsteady = (ref.std() / ref.mean()) * 100

    return covsteady[0]


def filter_rawemg(emgfile, order=2, lowcut=20, highcut=500):
    """
    Band-pass filter the RAW_SIGNAL.

    The filter is a Zero-lag band-pass Butterworth.

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile.
    order : int, default 2
        The filter order.
    lowcut : int, default 20
        The lower cut-off frequency in Hz.
    highcut : int, default 500
        The higher cut-off frequency in Hz.

    Returns
    -------
    filteredrawsig : dict
        The dictionary containing the emgfile with a filtered RAW_SIGNAL.
        Currently, the returned filteredrawsig cannot be accurately compressed
        when using the functions ``save_json_emgfile()`` and ``asksavefile()``.
        We therefore suggest you to save the unfiltered emgfile if you want to
        obtain maximum compression.

    See also
    --------
    - filter_refsig : low-pass filter the REF_SIGNAL.
    """

    filteredrawsig = copy.deepcopy(emgfile)

    # Calculate the components of the filter and apply them with filtfilt to
    # obtain Zero-lag filtering. sos should be preferred over filtfilt as
    # second-order sections have fewer numerical problems.
    sos = signal.butter(
        N=order,
        Wn=[lowcut, highcut],
        btype="bandpass",
        output="sos",
        fs=filteredrawsig["FSAMP"],
    )
    for col in filteredrawsig["RAW_SIGNAL"]:
        filteredrawsig["RAW_SIGNAL"][col] = signal.sosfiltfilt(
            sos,
            x=filteredrawsig["RAW_SIGNAL"][col],
        )

    return filteredrawsig


def filter_refsig(emgfile, order=4, cutoff=15):
    """
    Low-pass filter the REF_SIGNAL.

    This function is used to low-pass filter the REF_SIGNAL and remove noise.
    The filter is a Zero-lag low-pass Butterworth.

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile.
    order : int, default 4
        The filter order.
    cutoff : int, default 15
        The cut-off frequency in Hz.

    Returns
    -------
    filteredrefsig : dict
        The dictionary containing the emgfile with a filtered REF_SIGNAL.

    See also
    --------
    - remove_offset : remove the offset from the REF_SIGNAL.
    - filter_rawemg : band-pass filter the RAW_SIGNAL.
    """

    filteredrefsig = copy.deepcopy(emgfile)

    # Calculate the components of the filter and apply them with filtfilt to
    # obtain Zero-lag filtering. sos should be preferred over filtfilt as
    # second-order sections have fewer numerical problems.
    sos = signal.butter(
        N=order,
        Wn=cutoff,
        btype="lowpass",
        output="sos",
        fs=filteredrefsig["FSAMP"],
    )
    filteredrefsig["REF_SIGNAL"][0] = signal.sosfiltfilt(
        sos,
        x=filteredrefsig["REF_SIGNAL"][0],
    )

    return filteredrefsig


def remove_offset(emgfile, offsetval=0, auto=0):
    """
    Remove the offset from the REF_SIGNAL.

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile.
    offsetval : float, default 0
        Value of the offset. If offsetval is 0 (default), the user will be
        asked to manually select an aerea to compute the offset value.
        Otherwise, the value passed to offsetval will be used.
        Negative offsetval can be passed.
    auto : int, default 0
        If auto > 0, the script automatically removes the offset based on the
        number of samples passed in input.

    Returns
    -------
    offs_emgfile : dict
        The dictionary containing the emgfile with a corrected offset of the
        REF_SIGNAL.

    See also
    --------
    - filter_refsig : low-pass filter REF_SIGNAL.
    """

    # Check that all the inputs are correct
    if not isinstance(offsetval, (float, int)):
        raise TypeError(
            f"offsetval must be one of the following types: float, int. {type(offsetval)} was passed instead."
        )
    if not isinstance(auto, (float, int)):
        raise TypeError(
            f"auto must be one of the following types: float, int. {type(auto)} was passed instead."
        )

    # Create the object to store the filtered refsig.
    # Create a deepcopy to avoid changing the original refsig
    offs_emgfile = copy.deepcopy(emgfile)

    # Act differently if automatic removal of the offset is active (>0) or not
    if auto <= 0:
        if offsetval != 0:
            # Directly subtract the offset value.
            offs_emgfile["REF_SIGNAL"][0] = offs_emgfile["REF_SIGNAL"][0] - offsetval

        else:
            # Select the area to calculate the offset
            # (average value of the selected area)
            title = (
                "Select the start/end area to calculate the offset by " +
                "hovering the mouse \nand pressing the 'a'-key. Wrong " +
                " points can be removed with right \nclick or canc/delete " +
                "key. When ready, press enter."
            )
            points = showselect(
                emgfile=offs_emgfile,
                title=title,
                titlesize=10,
            )
            start_, end_ = points[0], points[1]

            offsetval = offs_emgfile["REF_SIGNAL"].loc[start_:end_].mean()
            # We need to convert the series offsetval into float
            offs_emgfile["REF_SIGNAL"][0] = (
                offs_emgfile["REF_SIGNAL"][0] - float(offsetval[0])
            )

    else:
        # Compute and subtract the offset value.
        offsetval = offs_emgfile["REF_SIGNAL"].iloc[0:auto].mean()
        # We need to convert the series offsetval into float
        offs_emgfile["REF_SIGNAL"][0] = (
            offs_emgfile["REF_SIGNAL"][0] - float(offsetval[0])
        )

    return offs_emgfile


def get_mvc(emgfile, how="showselect", conversion_val=0):
    """
    Measure the maximum voluntary contraction (MVC).

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile with the reference signal.
    how : str {"showselect", "all"}, default "showselect"

        ``showselect``
            Ask the user to select the area where to calculate the MVC
            with a GUI.

        ``all``
            Calculate the MVC on the entire file.
    conversion_val : float or int, default 0
        The conversion value to multiply the original reference signal.
        I.e., if the original reference signal is in kilogram (kg) and
        conversion_val=9.81, the output will be in Newton (N).
        If conversion_val=0 (default), the results will simply be in the
        original measure unit. conversion_val can be any custom int or float.

    Returns
    -------
    mvc : float
        The MVC value in the original (or converted) unit of measurement.

    See also
    --------
    - compute_rfd : calculate the RFD.
    - remove_offset : remove the offset from the REF_SIGNAL.
    - filter_refsig : low-pass filter REF_SIGNAL.

    Examples
    --------
    Load the EMG file, remove reference signal offset and get MVC value.

    >>> import openhdemg.library as emg
    >>> emg_refsig = emg.askopenfile(filesource="OTB_REFSIG")
    >>> offs_refsig = emg.remove_offset(emgfile=emg_refsig)
    >>> mvc = emg.get_mvc(emgfile=offs_refsig )
    >>> mvc
    50.72

    The process can be automated by bypassing the GUI and
    calculating the MVC of the entire file.

    >>> import openhdemg.library as emg
    >>> emg_refsig = emg.askopenfile(filesource="OTB_REFSIG")
    >>> mvc = emg.get_mvc(emgfile=emg_refsig, how="all")
    >>> print(mvc)
    50.86
    """

    if how == "all":
        mvc = emgfile["REF_SIGNAL"].max()

    elif how == "showselect":
        # Select the area to measure the MVC (maximum value)
        title = (
            "Select the start/end area to compute MVC by hovering the " +
            "mouse \nand pressing the 'a'-key. Wrong points can be removed " +
            "with right \nclick or canc/delete key. When ready, press enter."
        )
        points = showselect(
            emgfile=emgfile,
            title=title,
            titlesize=10,
        )
        start_, end_ = points[0], points[1]

        mvc = emgfile["REF_SIGNAL"].loc[start_:end_].max()

    else:
        raise ValueError(
            f"how must be one of 'showselect' or 'all', {how} was passed instead"
        )

    mvc = float(mvc[0])

    if conversion_val != 0:
        mvc = mvc * conversion_val

    return mvc


def compute_rfd(
    emgfile,
    ms=[50, 100, 150, 200],
    startpoint=None,
    conversion_val=0,
):
    """
    Calculate the RFD.

    Rate of force development (RFD) is reported as X/Sec
    where "X" is the unit of measurement based on conversion_val.

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile with the reference signal.
    ms : list, default [50, 100, 150, 200]
        Milliseconds (ms). A list containing the ranges in ms to calculate the
        RFD.
    startpoint : None or int, default None
        The starting point to calculate the RFD in samples,
        If None, the user will be requested to manually select the starting
        point.
    conversion_val : float or int, default 0
        The conversion value to multiply the original reference signal.
        I.e., if the original reference signal is in kilogram (kg) and
        conversion_val=9.81, the output will be in Newton/Sec (N/Sec).
        If conversion_val=0 (default), the results will simply be Original
        measure unit/Sec. conversion_val can be any custom int or float.

    Returns
    -------
    rfd : pd.DataFrame
        A pd.DataFrame containing the RFD at the different times.

    See also
    --------
    - get_mvif : measure the MViF.
    - remove_offset : remove the offset from the REF_SIGNAL.
    - filter_refsig : low-pass filter REF_SIGNAL.

    Examples
    --------
    Load the EMG file, low-pass filter the reference signal and compute RFD.

    >>> import openhdemg.library as emg
    >>> emg_refsig = emg.askopenfile(filesource="OTB_REFSIG")
    >>> filteredrefsig  = emg.filter_refsig(
    ...     emgfile=emg_refsig,
    ...     order=4,
    ...     cutoff=15,
    ... )
    >>> rfd = emg.compute_rfd(
    ...     emgfile=filteredrefsig,
    ...     ms=[50, 100, 200],
    ...     conversion_val=9.81,
    ...     )
    >>> rfd
            50         100        200
    0  68.34342  79.296188  41.308215

    The process can be automated by bypassing the GUI.

    >>> import openhdemg.library as emg
    >>> emg_refsig = emg.askopenfile(filesource="OTB_REFSIG")
    >>> filteredrefsig  = emg.filter_refsig(
    ...     emgfile=emg_refsig,
    ...     order=4,
    ...     cutoff=15,
    ...     )
    >>> rfd = emg.compute_rfd(
    ...     emgfile=filteredrefsig,
    ...     ms=[50, 100, 200],
    ...     startpoint=3568,
    ...     )
    >>> rfd
            50         100        200
    0  68.34342  79.296188  41.308215
    """

    # Check if the startpoint was passed
    if isinstance(startpoint, int):
        start_ = startpoint
    else:
        # Otherwise select the starting point for the RFD
        title = (
            "Select the start/end area to compute the RFD by hovering the " +
            "mouse \nand pressing the 'a'-key. Wrong points can be removed " +
            "with right \nclick or canc/delete key. When ready, press enter."
        )
        points = showselect(
            emgfile,
            title=title,
            titlesize=10,
            nclic=1,
        )
        start_ = points[0]

    # Create a dict to add the RFD
    rfd_dict = dict.fromkeys(ms, None)
    # Loop through the ms list and calculate the respective rfd.
    for thisms in ms:
        ms_insamples = round((int(thisms) * emgfile["FSAMP"]) / 1000)

        n_0 = emgfile["REF_SIGNAL"].loc[start_]
        n_next = emgfile["REF_SIGNAL"].loc[start_ + ms_insamples]

        rfdval = (n_next - n_0) / (thisms / 1000)
        # (ms/1000 to convert mSec in Sec)

        rfd_dict[thisms] = rfdval

    rfd = pd.DataFrame(rfd_dict)

    if conversion_val != 0:
        rfd = rfd * conversion_val

    return rfd


def compute_svr(
    emgfile,
    gammain=1/1.6,
    regparam=1/0.370,
    endpointweights_numpulses=5,
    endpointweights_magnitude=5,
    discontfiring_dur=1.0,
):
    """
    Fit MU discharge rates with Support Vector Regression, nonlinear
    regression.

    Provides smooth and continous estimates of discharge rate useful for
    quantification and visualisation. Suggested hyperparameters and framework
    from Beauchamp et. al., 2022
    https://doi.org/10.1088/1741-2552/ac4594

    Author: James (Drew) Beauchamp

    Parameters
    ----------
    emgfile : dict
        The dictionary containing the emgfile.
    gammain : float,  default 1/1.6
        The kernel coefficient.
    regparam : float,  default 1/0.370
        The regularization parameter, must be positive.
    endpointweights_numpulses : int, default 5
        Number of discharge instances at the start and end of MU firing to
        apply a weighting coefficient.
    endpointweights_magnitude : int, default 5
        The scaling factor applied to the number of pulses provided by
        endpointweights_numpulses.
        The scaling is applied to the regularization parameter, per sample.
        Larger values force the classifier to put more emphasis on the number
        of discharge instances at the start and end of firing provided by
        endpointweights_numpulses.
    discontfiring_dur : int, default 1
        Duration of time in seconds that defines an instnance of discontinuous
        firing. SVR fits will not be returned at points of discontinuity.

    Returns
    -------
    svrfits : pd.DataFrame
        A pd.DataFrame containing the smooth/continous MU discharge rates and
        corresponding time vectors.

    See also
    --------
    - compute_deltaf : quantify delta F via paired motor unit analysis.

    Examples
    --------
    Quantify svr fits.

    >>> import openhdemg.library as emg
    >>> import pandas as pd
    >>> emgfile = emg.emg_from_samplefile()
    >>> emgfile = emg.sort_mus(emgfile=emgfile)
    >>> svrfits = emg.compute_svr(emgfile)

    Quick plot showing the results.

    >>> smoothfits = pd.DataFrame(svrfits["gensvr"]).transpose()
    >>> emg.plot_smoothed_dr(
    >>>     emgfile,
    >>>     smoothfits=smoothfits,
    >>>     munumber="all",
    >>>     addidr=False,
    >>>     stack=True,
    >>>     addrefsig=True,
    >>> )
    """

    # TODO input checking and edge cases
    idr = compute_idr(emgfile)  # Calc IDR

    svrfit_acm = []
    svrtime_acm = []
    gensvr_acm = []
    for mu in range(len(idr)):  # For all MUs
        # Skip if no data
        if idr[mu].size==0:
            svrfit_acm.append([])
            svrtime_acm.append([])
            gensvr_acm.append(np.nan*np.ones(emgfile["EMG_LENGTH"]))

        else:            # Train the model on the data.
            # Time vector, removing first element.
            xtmp = np.transpose([idr[mu].timesec[1:]])
            # Discharge rates, removing first element, since DR has been assigned
            # to second pulse.
            ytmp = idr[mu].idr[1:].to_numpy()
            # Time between discharges, will use for discontinuity calc
            xdiff = idr[mu].diff_mupulses[2:].values
            # Motor unit pulses, samples
            mup = np.array(idr[mu].mupulses[1:].values)

            # Defining weight vector. A scaling applied to the regularization
            # parameter, per sample.
            smpwht = np.ones(len(ytmp))
            smpwht[0:endpointweights_numpulses-1] = endpointweights_magnitude
            smpwht[(len(ytmp)-(endpointweights_numpulses-1)):len(ytmp)] = endpointweights_magnitude

            # Create an SVR model with a gausian kernel and supplied hyperparams.
            # Origional hyperparameters from Beauchamp et. al., 2022:
            # https://doi.org/10.1088/1741-2552/ac4594
            svr = SVR(
                kernel='rbf', gamma=gammain, C=np.abs(regparam),
                epsilon=iqr(ytmp)/11,
            )
            svr.fit(xtmp, ytmp, sample_weight=smpwht)

            # Defining prediction vector
            # TODO need to add custom range.
            # From the second firing to the end of firing, in samples.
            predind = np.arange(mup[0], mup[-1]+1)
            predtime = (predind/emgfile["FSAMP"]).reshape(-1, 1)  # In time (s)
            newtm = []
            # Initialise nan vector for tracking fits aligned in time. Usefull for
            # later quant metrics.
            gen_svr = np.nan*np.ones(emgfile["EMG_LENGTH"])

            # Check for discontinous firing
            bkpnt = mup[
                np.where((xdiff > (discontfiring_dur * emgfile["FSAMP"])))[0]
            ]
            bkpnt = bkpnt[np.where(bkpnt != mup[-1])]

            if len(bkpnt) == 1:
                if bkpnt[0] == mup[0]:  # When first firing is the only discontinuity
                    bkpnt = []
                    predind = np.arange(mup[1], mup[-1]+1)
                    predtime = (predind/emgfile["FSAMP"]).reshape(-1, 1)

            # Make predictions on the data
            if len(bkpnt) > 0:  # If there is a point of discontinuity
                if bkpnt[0] == mup[0]:  # When first firing is discontinuity
                    smoothfit = np.nan*np.ones(1)
                    newtm = np.nan*np.ones(1)
                    bkpnt = bkpnt[1:]

                tmptm = predtime[
                    0: np.where(
                        (bkpnt[0] >= predind[0:-1]) & (bkpnt[0] < predind[1:])
                    )[0][0],
                ]  # Break up time vector for first continous range of firing
                smoothfit = svr.predict(tmptm)  # Predict with svr model
                newtm = np.append(newtm,tmptm,)  # Track new time vector

                tmpind = predind[
                    0: np.where(
                        (bkpnt[0] >= predind[0:-1]) & (bkpnt[0] < predind[1:])
                    )[0][0]
                ]  # Sample vector of first continous range of firing
                
                # Fill corresponding sample indices with svr fit
                gen_svr[tmpind.astype(np.int64)] = smoothfit
                # Add last firing as discontinuity
                bkpnt = np.append(bkpnt, mup[-1])
                for ii in range(len(bkpnt)-1):  # All instances of discontinuity
                    curind = np.where(
                        (bkpnt[ii] > predind[0:-1]) & (bkpnt[ii] <= predind[1:])
                    )[0][0]  # Current index of discontinuity
                    nextind = np.where(
                        (bkpnt[ii+1] > predind[0:-1]) & (bkpnt[ii+1] <= predind[1:])
                    )[0][0]  # Next index of discontinuity

                    # MU firing before discontinuity
                    curmup = np.where(mup == bkpnt[ii])[0][0]
                    curind_nmup = np.where(
                        (mup[curmup+1] > predind[0:-1]) & (mup[curmup+1] <= predind[1:])
                    )[0][0]  # MU firing after discontinuity

                    # If the next discontinuity is the next MU firing, nan fill
                    if curind_nmup >= nextind:
                        # Edge case NEED TO CHECK THE GREATER THAN CASE>> WHY TODO
                        smoothfit = np.append(smoothfit, np.nan*np.ones(1))
                        newtm = np.append(newtm, np.nan*np.ones(1))
                    else:  # Fit next continuous region of firing
                        smoothfit = np.append(
                            smoothfit,
                            np.nan*np.ones(len(predtime[curind:curind_nmup])-2),
                        )
                        smoothfit = np.append(
                            smoothfit, svr.predict(predtime[curind_nmup:nextind]),
                        )
                        newtm = np.append(
                            newtm,
                            np.nan*np.ones(len(predtime[curind:curind_nmup])-2),
                        )
                        newtm = np.append(newtm, predtime[curind_nmup:nextind],)
                        gen_svr[predind[curind_nmup:nextind]] = svr.predict(
                            predtime[curind_nmup:nextind]
                        )
            else:
                smoothfit = svr.predict(predtime)
                newtm = predtime
                gen_svr[predind] = smoothfit


            # Append fits, new time vect, time aligned fits
            svrfit_acm.append(smoothfit.copy())
            svrtime_acm.append(np.squeeze(newtm.copy()))
            gensvr_acm.append(gen_svr.copy())

    svrfits = {
        "svrfit": svrfit_acm,
        "svrtime": svrtime_acm,
        "gensvr": gensvr_acm,
    }

    return svrfits
