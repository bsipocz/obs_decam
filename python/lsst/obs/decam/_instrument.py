# This file is part of obs_decam.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (http://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Butler instrument description for the Dark Energy Camera.
"""

__all__ = ("DarkEnergyCamera",)

import os
from functools import lru_cache

from lsst.afw.cameraGeom import makeCameraFromPath, CameraConfig
from lsst.obs.base import Instrument
from lsst.obs.base.gen2to3 import BandToPhysicalFilterKeyHandler, TranslatorFactory
from lsst.obs.decam.decamFilters import DECAM_FILTER_DEFINITIONS

from lsst.daf.butler.core.utils import getFullTypeName
from lsst.utils import getPackageDir


class DarkEnergyCamera(Instrument):
    filterDefinitions = DECAM_FILTER_DEFINITIONS
    policyName = "decam"
    obsDataPackage = "obs_decam_data"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        packageDir = getPackageDir("obs_decam")
        self.configPaths = [os.path.join(packageDir, "config")]

    @classmethod
    def getName(cls):
        return "DECam"

    def getCamera(self):
        path = os.path.join(getPackageDir("obs_decam"), self.policyName, "camGeom")
        return self._getCameraFromPath(path)

    @staticmethod
    @lru_cache()
    def _getCameraFromPath(path):
        """Return the camera geometry given solely the path to the location
        of that definition."""
        config = CameraConfig()
        config.load(os.path.join(path, "camera.py"))
        return makeCameraFromPath(
            cameraConfig=config,
            ampInfoPath=path,
            shortNameFunc=lambda name: name.replace(" ", "_"),
        )

    def register(self, registry):
        camera = self.getCamera()
        obsMax = 2**31
        with registry.transaction():
            registry.syncDimensionData(
                "instrument",
                {
                    "name": self.getName(), "detector_max": 64, "visit_max": obsMax, "exposure_max": obsMax,
                    "class_name": getFullTypeName(self),
                }
            )

            for detector in camera:
                registry.syncDimensionData(
                    "detector",
                    {
                        "instrument": self.getName(),
                        "id": detector.getId(),
                        "full_name": detector.getName(),
                        "name_in_raft": detector.getName()[1:],
                        "raft": detector.getName()[0],
                        "purpose": str(detector.getType()).split(".")[-1],
                    }
                )

            self._registerFilters(registry)

    def getRawFormatter(self, dataId):
        # local import to prevent circular dependency
        from .rawFormatter import DarkEnergyCameraRawFormatter
        return DarkEnergyCameraRawFormatter

    def makeDataIdTranslatorFactory(self) -> TranslatorFactory:
        # Docstring inherited from lsst.obs.base.Instrument.
        factory = TranslatorFactory()
        factory.addGenericInstrumentRules(self.getName(), calibFilterType="band",
                                          detectorKey="ccdnum")
        # DECam calibRegistry entries are bands, but we need physical_filter
        # in the gen3 registry.
        factory.addRule(BandToPhysicalFilterKeyHandler(self.filterDefinitions),
                        instrument=self.getName(),
                        gen2keys=("filter",),
                        consume=("filter",),
                        datasetTypeName="cpFlat")
        return factory
