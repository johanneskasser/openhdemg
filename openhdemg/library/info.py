"""
This module contains all the information regarding:

- Data
    - Structures of data
    - How to access data

- Abbreviations

- AboutUs
- Contacts
- Links
- CiteUs
"""

import json
from textwrap import dedent


class info:
    """
    A class used to obtain info.

    Methods
    -------
    data(emgfile)
        Print a description of the emgfile data structure.
    abbreviations()
        Print common abbreviations.
    aboutus()
        Print informations about the library and the authors.
    contacts()
        Print the contacts.
    links()
        Print a collection of useful links.
    citeus()
        Print how to cite the project.
    """

    def __init__(self):
        pass

    def data(self, emgfile):
        """
        Print a description of the emgfile data structure.

        Print a detailed description of the emgfile data structure and of how
        to access the contained elements.

        Parameters
        ----------
        emgfile : dict
            The dictionary containing the emgfile.

        Examples
        --------
        >>> import openhdemg.library as emg
        >>> emgfile = emg.askopenfile(filesource="DEMUSE")
        >>> emg.info().data(emgfile)
        emgfile type is:
        <class 'dict'>
        emgfile keys are:
        dict_keys(['SOURCE', 'FILENAME', 'RAW_SIGNAL', 'REF_SIGNAL', 'ACCURACY', 'IPTS', 'MUPULSES', 'FSAMP', 'IED', 'EMG_LENGTH', 'NUMBER_OF_MUS', 'BINARY_MUS_FIRING', 'EXTRAS'])
        Any key can be acced as emgfile[key].
        emgfile['SOURCE'] is a <class 'str'> of value:
        DEMUSE
        .
        .
        .
        """

        if emgfile["SOURCE"] in ["DEMUSE", "OTB", "CUSTOMCSV", "DELSYS"]:
            print("\nData structure of the emgfile")
            print("-----------------------------\n")
            print(f"emgfile type is:\n{type(emgfile)}\n")
            print(f"emgfile keys are:\n{emgfile.keys()}\n")
            print("Any key can be acced as emgfile[key].\n")
            print(f"emgfile['SOURCE'] is a {type(emgfile['SOURCE'])} of value:\n{emgfile['SOURCE']}\n")
            print(f"emgfile['FILENAME'] is a {type(emgfile['FILENAME'])} of value:\n{emgfile['FILENAME']}\n")
            print("MUST NOTE: emgfile from OTB has 64 channels, from DEMUSE 65 (includes empty channel).")
            print(f"emgfile['RAW_SIGNAL'] is a {type(emgfile['RAW_SIGNAL'])} of value:\n{emgfile['RAW_SIGNAL']}\n")
            print(f"emgfile['REF_SIGNAL'] is a {type(emgfile['REF_SIGNAL'])} of value:\n{emgfile['REF_SIGNAL']}\n")
            print(f"emgfile['ACCURACY'] is a {type(emgfile['ACCURACY'])} of value:\n{emgfile['ACCURACY']}\n")
            print(f"emgfile['IPTS'] is a {type(emgfile['IPTS'])} of value:\n{emgfile['IPTS']}\n")
            print(f"emgfile['MUPULSES'] is a {type(emgfile['MUPULSES'])} of length depending on total MUs number.")
            if emgfile['NUMBER_OF_MUS'] > 0:  # Manage exceptions
                print("MUPULSES for each MU can be accessed as emgfile['MUPULSES'][MUnumber].\n")
                print(f"emgfile['MUPULSES'][0] is a {type(emgfile['MUPULSES'][0])} of value:\n{emgfile['MUPULSES'][0]}\n")
            print(f"emgfile['FSAMP'] is a {type(emgfile['FSAMP'])} of value:\n{emgfile['FSAMP']}\n")
            print(f"emgfile['IED'] is a {type(emgfile['IED'])} of value:\n{emgfile['IED']}\n")
            print(f"emgfile['EMG_LENGTH'] is a {type(emgfile['EMG_LENGTH'])} of value:\n{emgfile['EMG_LENGTH']}\n")
            print(f"emgfile['NUMBER_OF_MUS'] is a {type(emgfile['NUMBER_OF_MUS'])} of value:\n{emgfile['NUMBER_OF_MUS']}\n")
            print(f"emgfile['BINARY_MUS_FIRING'] is a {type(emgfile['BINARY_MUS_FIRING'])} of value:\n{emgfile['BINARY_MUS_FIRING']}\n")
            print(f"emgfile['EXTRAS'] is a {type(emgfile['EXTRAS'])} of value:\n{emgfile['EXTRAS']}\n")

        elif emgfile["SOURCE"] in ["OTB_REFSIG", "CUSTOMCSV_REFSIG", "DELSYS_REFSIG"]:
            print("\nData structure of the emgfile")
            print("-----------------------------\n")
            print(f"emgfile type is:\n{type(emgfile)}\n")
            print(f"emgfile keys are:\n{emgfile.keys()}\n")
            print("Any key can be acced as emgfile[key].\n")
            print(f"emgfile['SOURCE'] is a {type(emgfile['SOURCE'])} of value:\n{emgfile['SOURCE']}\n")
            print(f"emgfile['FILENAME'] is a {type(emgfile['FILENAME'])} of value:\n{emgfile['FILENAME']}\n")
            print(f"emgfile['FSAMP'] is a {type(emgfile['FSAMP'])} of value:\n{emgfile['FSAMP']}\n")
            print(f"emgfile['REF_SIGNAL'] is a {type(emgfile['REF_SIGNAL'])} of value:\n{emgfile['REF_SIGNAL']}\n")
            print(f"emgfile['EXTRAS'] is a {type(emgfile['EXTRAS'])} of value:\n{emgfile['EXTRAS']}\n")

        else:
            raise ValueError(f"Source '{emgfile['SOURCE']}' not recognised")

    def abbreviations(self):
        """
        Print common abbreviations.

        Returns
        -------
        abbr : dict
            The dictionary containing the abbreviations and their meaning.

        Examples
        --------
        >>> import openhdemg.library as emg
        >>> emg.info().abbreviations()
        "COV": "Coefficient of variation",
        "DERT": "DERecruitment threshold",
        "DD": "Double differential",
        "DR": "Discharge rate",
        "FSAMP": "Sampling frequency",
        "IDR": "Instantaneous discharge rate",
        "IED": "Inter electrode distance",
        "IPTS": "Impulse train (decomposed source)",
        "MU": "Motor units",
        "MUAP": "MUs action potential",
        "PIC": "Persistent inward currents",
        "PNR": "Pulse to noise ratio",
        "RT": "Recruitment threshold",
        "SD": "Single differential",
        "SIL": "Silhouette score",
        "STA": "Spike-triggered average",
        "SVR": "Support Vector Regression",
        "XCC": "Cross-correlation coefficient"
        """

        abbr = {
            "COV": "Coefficient of variation",
            "DERT": "DERecruitment threshold",
            "DD": "Double differential",
            "DR": "Discharge rate",
            "FSAMP": "Sampling frequency",
            "IDR": "Instantaneous discharge rate",
            "IED": "Inter electrode distance",
            "IPTS": "Impulse train (decomposed source)",
            "MU": "Motor units",
            "MUAP": "MUs action potential",
            "PIC": "Persistent inward currents",
            "PNR": "Pulse to noise ratio",
            "RT": "Recruitment threshold",
            "SD": "Single differential",
            "SIL": "Silhouette score",
            "STA": "Spike-triggered average",
            "SVR": "Support Vector Regression",
            "XCC": "Cross-correlation coefficient",
        }

        # Pretty dict printing
        print("\nAbbreviations:\n")
        print(json.dumps(abbr, indent=4))

        return abbr

    def aboutus(self):
        """
        Print informations about the library and the authors.

        Returns
        -------
        about, us : str
            The strings containing the information.

        Examples
        --------
        >>> import openhdemg.library as emg
        >>> emg.info().aboutus()
        The openhdemg project was born in 2022 with the aim to provide a
        free and open-source framework to analyse HIGH-DENSITY EMG
        recordings...
        """

        about = """
            About
            -----

            The openhdemg project was born in 2022 with the aim to provide a
            free and open-source framework to analyse HIGH-DENSITY EMG
            recordings.

            The field of EMG analysis in humans has always be characterised by
            little or no software available for signal post-processing and
            analysis and this forced users to code their own scripts.
            Although coding can be funny, it can lead to a number of problems,
            especially when the utilised scripts are not shared open-source.
            Why?

            - If different users use different scripts, the results can differ.
            - Any code can contain errors, if the code is not shared, the error
                will never be known and it will repeat in the following
                analysis.
            - There is a huge difference between the paper methods and the
                practical implementation of a script. Only rarely it will be
                possible to reproduce a script solely based on words (thus
                making the reproducibility of a study unrealistic).
            - Anyone who doesn't code, will not be able to analyse the
                recordings.

            In order to overcome these (and many other) problems of private
            scripts, we developed a fully transparent framework with
            appropriate documentation to allow all the users to check the
            correctness of the script and to perform reproducible analysis.

            This project is aimed at users that already know the Python
            language, as well as for those willing to learn it and even for
            those not interested in coding thanks to a friendly graphical user
            interface (GUI).

            Both the openhdemg project and its contributors adhere to the Open
            Science Principles and especially to the idea of public release of
            data and other scientific resources necessary to conduct honest
            research.
            """

        us = """
        Us
        --

        For the full list of contributors and developers visit:
        https://www.giacomovalli.com/openhdemg/about-us/
        """

        # Make Text Bold and Italic with Escape Sequence
        # '\x1B[3m' makes it italic
        # '\x1B[1m' makes it bold
        # '\x1B[1;3m' makes it bold and italic
        # '\x1B[0m' is the closing tag

        # Pretty print indented multiline str
        print(dedent(about))
        print(dedent(us))

        return about, us

    def contacts(self):
        """
        Print the contacts.

        Returns
        -------
        contacts : dict
            The dictionary containing the contact details.

        Examples
        --------
        >>> import openhdemg.library as emg
        >>> emg.info().contacts()
        "Primary contact": "openhdemg@gmail.com",
        "Twitter": "@openhdemg",
        "Maintainer": "Giacomo Valli",
        "Maintainer Email": "giacomo.valli@unibs.it",
        """

        contacts = {
            "Primary contact": "openhdemg@gmail.com",
            "Twitter": "@openhdemg",
            "Maintainer": "Giacomo Valli",
            "Maintainer Email": "giacomo.valli@unibs.it",
        }

        # Pretty dict printing
        print("\nContacts:\n")
        print(json.dumps(contacts, indent=4))

        return contacts

    def links(self):
        """
        Print a collection of useful links.

        Returns
        -------
        links : dict
            The dictionary containing the useful links.

        Examples
        --------
        >>> import openhdemg.library as emg
        >>> emg.info().links()
        """

        links = {
            "Project Website": "https://www.giacomovalli.com/openhdemg/",
            "Release Notes": "https://www.giacomovalli.com/openhdemg/what%27s-new/",
            "Cite Us": "https://www.giacomovalli.com/openhdemg/cite-us/",
            "Discussion Forum": "https://github.com/GiacomoValliPhD/openhdemg/discussions",
            "Report Bugs": "https://github.com/GiacomoValliPhD/openhdemg/issues",
        }

        # Pretty dict printing
        print("\nLinks:\n")
        print(json.dumps(links, indent=4))

        return links

    def citeus(self):
        """
        Print how to cite the project.

        Returns
        -------
        cite : str
            The full citation.

        Examples
        --------
        >>> import openhdemg.library as emg
        >>> emg.info().citeus()
        """

        cite = (
            "Valli G, Ritsche P, Casolo A, Negro F, De Vito G. " +
            "Tutorial: Analysis of central and peripheral motor unit " +
            "properties from decomposed High-Density surface EMG signals " +
            "with openhdemg. J Electromyogr Kinesiol. 2024 Feb;74:102850. " +
            "doi: 10.1016/j.jelekin.2023.102850. Epub 2023 Nov 30."
        )

        # Pretty dict printing
        print("\nCite Us:\n")
        print(cite)
        print("\n")

        return cite
