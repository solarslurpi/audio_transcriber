###########################################################################################
# Author: HappyDay Johnson
# Version: 0.01
# Date: 2024-03-20
# Summary: This test suite tests the functionality and completeness obackground processing
# of mp3 files within the GDrive folder containing the mp3 files as defined within the
# environmental settings.
#
# License Information: MIT License
#
# Copyright (c) 2024 HappyDay Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###########################################################################################

import pytest

from env_settings_code import get_settings
from gdrive_helper_code import GDriveHelper  # Adjust the import path according to your project structure

@pytest.fixture
def mp3_gdrive_id():
    settings = get_settings()
    return settings.gdrive_mp3_folder_id

@pytest.mark.asyncio
async def test_workflow_status_in_gdrive_files(mp3_gdrive_id):
    gdrive_helper = GDriveHelper()  # Ensure GDriveHelper is properly initialized for the test
    files_to_transcribe = await gdrive_helper.list_files_to_transcribe(mp3_gdrive_id)

    for gfile in files_to_transcribe:
        # Assuming gfile is an instance containing the Google Drive file ID and other metadata
        status_info = gdrive_helper.get_status_field(gfile)
        print(f"The status of this gfile is: {status_info['status']}")
