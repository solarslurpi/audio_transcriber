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

@pytest.mark.asyncio
async def test_get_mp3_gdrive_file_list():
    settings = get_settings()
    mp3_gdrive_folder = settings.gdrive_mp3_folder_id
    # Read the first few bytes to check if the file has content
    assert valid_UploadFile,UploadFile
    content = await valid_UploadFile.read(10)  # Read the first 10 bytes
    # Check if anything was read
    if content:
        print("The file has content.")
    else:
        print("The file is empty.")
    # Reset the pointer to the beginning of the file for future reads
    await valid_UploadFile.seek(0)