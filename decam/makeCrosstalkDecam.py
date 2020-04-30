#!/usr/bin/env python3
"""Convert a DECam crosstalk text table into LSST CrosstalkCalibs.
"""
import argparse
import numpy as np
import os.path
import sys

import lsst.ip.isr as ipIsr
from lsst.daf.base import PropertyList
from lsst.obs.decam import DecamMapper


def makeDetectorCrosstalk(dataDict):
    """Generate and write CrosstalkCalib from dictionary.

    Parameters
    ----------
    dataDict : `dict`
        Dictionary from ``readFile`` containing crosstalk definition.
    """
    dataDict['coeffs'] = dataDict['coeffs'].transpose()

    decamCT = ipIsr.crosstalk.CrosstalkCalib.fromDict(dataDict)
    decamCT.updateMetadata(setDate=True)
    outDir = DecamMapper.getCrosstalkDir()
    detName = dataDict['DETECTOR']
    decamCT.writeFits(f"{outDir}/{detName}.fits")


def readFile(fromFile):
    """Construct crosstalk dictionary-of-dictionaries from fromFile.

    Parameters
    ----------
    fromFile : `str`
        File containing crosstalk coefficient information.

    Results
    -------
    outDict : `dict` [`str` : `dict`]
        Output dictionary, keyed on victim detector names, containing
        `lsst.ip.isr.CrosstalkCalib`'s expected dictionary format.

    Raises
    ------
    RuntimeError :
        Raised if the detector is not known.
    """
    ampIndexMap = {'A': 0, 'B': 1}
    detMap = {'ccd01': 'S29', 'ccd02': 'S30', 'ccd03': 'S31', 'ccd04': 'S25', 'ccd05': 'S26',
              'ccd06': 'S27', 'ccd07': 'S28', 'ccd08': 'S20', 'ccd09': 'S21', 'ccd10': 'S22',
              'ccd11': 'S23', 'ccd12': 'S24', 'ccd13': 'S14', 'ccd14': 'S15', 'ccd15': 'S16',
              'ccd16': 'S17', 'ccd17': 'S18', 'ccd18': 'S19', 'ccd19': 'S8', 'ccd20': 'S9',
              'ccd21': 'S10', 'ccd22': 'S11', 'ccd23': 'S12', 'ccd24': 'S13', 'ccd25': 'S1',
              'ccd26': 'S2', 'ccd27': 'S3', 'ccd28': 'S4', 'ccd29': 'S5', 'ccd30': 'S6',
              'ccd31': 'S7', 'ccd32': 'N1', 'ccd33': 'N2', 'ccd34': 'N3', 'ccd35': 'N4',
              'ccd36': 'N5', 'ccd37': 'N6', 'ccd38': 'N7', 'ccd39': 'N8', 'ccd40': 'N9',
              'ccd41': 'N10', 'ccd42': 'N11', 'ccd43': 'N12', 'ccd44': 'N13', 'ccd45': 'N14',
              'ccd46': 'N15', 'ccd47': 'N16', 'ccd48': 'N17', 'ccd49': 'N18', 'ccd50': 'N19',
              'ccd51': 'N20', 'ccd52': 'N21', 'ccd53': 'N22', 'ccd54': 'N23', 'ccd55': 'N24',
              'ccd56': 'N25', 'ccd57': 'N26', 'ccd58': 'N27', 'ccd59': 'N28', 'ccd60': 'N29',
              'ccd61': 'N30', 'ccd62': 'N31',
              }
    outDict = dict()
    with open(fromFile) as f:
        for line in f:
            li = line.strip()
            if not li.startswith('#'):
                elem = li.split()

                victimDetAmp = elem[0]
                sourceDetAmp = elem[1]
                coeff = float(elem[2])

                if 'A' in victimDetAmp:
                    victimAmp = 'A'
                elif 'B' in victimDetAmp:
                    victimAmp = 'B'
                else:
                    raise RuntimeError(f"Unknown amp: {victimDetAmp}")

                if 'A' in sourceDetAmp:
                    sourceAmp = 'A'
                elif 'B' in sourceDetAmp:
                    sourceAmp = 'B'
                else:
                    raise RuntimeError(f"Unknown amp: {sourceDetAmp}")

                victimDet = victimDetAmp.replace(victimAmp, "")
                sourceDet = sourceDetAmp.replace(sourceAmp, "")
                victimDet = detMap[victimDet]
                sourceDet = detMap[sourceDet]

                victimAmp = ampIndexMap[victimAmp]
                sourceAmp = ampIndexMap[sourceAmp]

                if victimDet not in outDict:
                    outDict[victimDet] = dict()
                    outDict[victimDet]['metadata'] = PropertyList()
                    outDict[victimDet]['metadata']['OBSTYPE'] = 'CROSSTALK'
                    outDict[victimDet]['interChip'] = dict()
                    outDict[victimDet]['crosstalkShape'] = (2, 2)
                    outDict[victimDet]['hasCrosstalk'] = True
                    outDict[victimDet]['nAmp'] = 2
                    if 'coeffs' not in outDict[victimDet]:
                        # shape=outDict[victimDet]['crosstalkShape'])
                        outDict[victimDet]['coeffs'] = np.zeros_like([], shape=(2, 2))

                if sourceDet == victimDet:
                    outDict[victimDet]['metadata']['DETECTOR'] = victimDet
                    outDict[victimDet]['metadata']['DETECTOR_SERIAL'] = "UNKNOWN"
                    outDict[victimDet]['DETECTOR'] = victimDet
                    outDict[victimDet]['DETECTOR_SERIAL'] = "UNKNOWN"
                    outDict[victimDet]['coeffs'][victimAmp][sourceAmp] = coeff
                else:
                    if sourceDet not in outDict[victimDet]['interChip']:
                        outDict[victimDet]['interChip'][sourceDet] = np.zeros_like([], shape=(2, 2))
                    outDict[victimDet]['interChip'][sourceDet][victimAmp][sourceAmp] = coeff
    return outDict


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a DECam crosstalk file into LSST CrosstalkCalibs.")
    parser.add_argument(dest="fromFile", help="DECam crosstalk file.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print data about each detector.")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing CrosstalkCalibs.")
    cmd = parser.parse_args()

    outDict = readFile(fromFile=cmd.fromFile)

    crosstalkDir = DecamMapper.getCrosstalkDir()
    if os.path.exists(crosstalkDir):
        if not cmd.force:
            print("Output directory %r exists; use --force to replace" % (crosstalkDir, ))
            sys.exit(1)
        print("Replacing data in crosstalk directory %r" % (crosstalkDir, ))
    else:
        print("Creating crosstalk directory %r" % (crosstalkDir, ))
        os.makedirs(crosstalkDir)
    for detName in outDict:
        if cmd.verbose:
            print(f"{detName}: has crosstalk? {outDict[detName]['hasCrosstalk']}")
            print(f"COEFF:\n{outDict[detName]['coeffs']}")
            for source in outDict[detName]['interChip']:
                print(f"INTERCHIP {source}:\n{outDict[detName]['interChip'][source]}")
        makeDetectorCrosstalk(dataDict=outDict[detName])
