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
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from audio_transcriber_code import AudioTranscriber
from gdrive_helper_code import GDriveHelper
from workflow_tracker_code import  WorkflowTracker
from pydantic_models import  GDriveInput



@pytest.fixture
def valid_mp3_gdrive_id():
    return '1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5'
@pytest.fixture
def valid_mp3_gdrive_input():
    return GDriveInput(gdrive_id='1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5')

@pytest.fixture
def valid_mp3_path():
    # Make sure this mp3 file exists. It could be any mp3 file with text for transcription.
    windows_file_path = r'C:\Users\happy\Documents\Projects\audio_to_transcript\test\test.mp3'
    return Path(windows_file_path)

@pytest.fixture
def valid_UploadFile(valid_mp3_path):
    file_content = valid_mp3_path.read_bytes()
    # Create a BytesIO object from the binary content
    file_like = BytesIO(file_content)
    # Create an UploadFile object. The filename and content_type can be adjusted as needed.
    upload_file = UploadFile(filename=valid_mp3_path.name, file=file_like)
        # Display the number of bytes in the original file
    upload_file.file.seek(0) # rewrind to beginning
    num_upload_bytes = len(upload_file.file.read()) # read to the end
    upload_file.file.seek(0) # rewind the file for the next reader.
    num_valid_mp3_bytes = valid_mp3_path.stat().st_size
    assert num_upload_bytes == num_valid_mp3_bytes
    return upload_file

@pytest.fixture
def init_WorkflowTracker_mp3(valid_mp3_gdrive_id,valid_mp3_path):
    WorkflowTracker.update(
    local_mp3_path=valid_mp3_path,
    input_mp3 = GDriveInput(gdrive_id=valid_mp3_gdrive_id)
    )
    print(f"WorkflowTrackerModel: {WorkflowTracker.get_model().model_dump_json(indent = 4)}")
    print(f"/n-----> input_mp3 type: {type(WorkflowTracker.get('input_mp3'))}")
    return



@pytest.mark.asyncio
async def test_check_upload_file_content(valid_UploadFile: UploadFile):
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

@pytest.mark.asyncio
async def test_login_success():
    gh = GDriveHelper()
     # Assert that the access token is present and not empty
    assert gh.gauth.credentials, "Access token should be returned"

def _run_asserts_for_local_mp3_path(mp3_gdrive_id, local_mp3_path):
    # Ensure mp3_path is an instance of Path and ends with '.mp3'
    assert isinstance(local_mp3_path, Path), "mp3_path should be a Path object"
    assert local_mp3_path.suffix == '.mp3', "The file should have an '.mp3' extension"
    # Check that the file at mp3_path contains bytes
    assert local_mp3_path.is_file(), "mp3_path should point to a file"
    assert local_mp3_path.stat().st_size > 0, "The file should contain bytes"
    # GDriveID
    assert isinstance(mp3_gdrive_id,str)
    assert len(mp3_gdrive_id) > 20 # Gdrive IDs are long...this is perhaps a naive check...

@pytest.mark.asyncio
async def test_copy_UploadFile_to_local_mp3_path(valid_UploadFile):
    transcriber = AudioTranscriber()
    mp3_gdrive_id, local_mp3_path = await transcriber.copy_uploadfile_to_local_mp3(valid_UploadFile)
    _run_asserts_for_local_mp3_path(mp3_gdrive_id, local_mp3_path)

@pytest.mark.asyncio
async def test_copy_gfile_to_local_mp3_path(valid_mp3_gdrive_input):
    '''
    Test the first major part of the code: Preparing the mp3 file for transcription.
    '''
    transcriber = AudioTranscriber()
    mp3_gdrive_id, local_mp3_path = await transcriber.copy_gfile_to_local_mp3(valid_mp3_gdrive_input)
    _run_asserts_for_local_mp3_path(mp3_gdrive_id, local_mp3_path)

@pytest.mark.asyncio
async def test_mp3_to_text_success(init_WorkflowTracker_mp3) : # pylint: disable=unused-argument
    transcriber = AudioTranscriber()
    transcription_text = await transcriber.transcribe_mp3()
    assert transcription_text is not None, "Transcription result should not be None"
    min_char_count = 100  # Example minimum character count
    assert len(transcription_text) >= min_char_count, f"Transcription text should contain at least {min_char_count} characters."
    assert isinstance(transcription_text, str), "Transcription result should be a string"
    assert len(transcription_text) > 0, "Transcription result should not be empty"

async def run_transcription_test_success():
    """Helper function to run the transcription test and perform common assertions."""
    transcriber = AudioTranscriber()
    transcription_text = await transcriber.transcribe()

    assert transcription_text is not None, "Transcription result should not be None"
    min_char_count = 100  # Example minimum character count
    assert len(transcription_text) >= min_char_count, f"Transcription text should contain at least {min_char_count} characters."
    assert isinstance(transcription_text, str), "Transcription result should be a string"
    assert len(transcription_text) > 0, "Transcription result should not be empty"

@pytest.mark.asyncio
async def test_audio_transcription_workflow_mp3_upload_success(init_WorkflowTracker_mp3): # pylint: disable=unused-argument
    """Test full transcription process for an UploadFile input."""
    await run_transcription_test_success()

@pytest.mark.asyncio
async def test_audio_transcription_workflow_mp3_gdrive_success(init_WorkflowTracker_mp3): # pylint: disable=unused-argument
    """Test full transcription process for a Google Drive file ID input."""

    await run_transcription_test_success()
