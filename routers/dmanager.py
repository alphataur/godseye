from fastapi import BackgroundTasks, Request, APIRouter
from pydantic import BaseModel
from typing import List, Any
# from ..common import successify, errorify



def successify(data):
    """
    Create a success response with provided data.
    
    Args:
        data (Any): Data to be returned in successful response
    
    Returns:
        dict: Standardized success response
    """
    return {
        "success": True,
        "error": False,
        "data": data
    }

def errorify(err):
    """
    Create an error response with provided error message.
    
    Args:
        err (str): Error message describing the failure
    
    Returns:
        dict: Standardized error response
    """
    return {
        "success": False,
        "error": err,
        "data": None
    }


# class AddDownloadRequest(BaseModel):
#     url: str
#     fpath: str

class DownloadStatusResponse(BaseModel):
    fpath: str
    url: str
    fingerprint: str
    elapsed: float
    offset: int
    length: int
    last_speed: float
    is_paused: bool
    is_removed: bool


DmanRouter = APIRouter()





@DmanRouter.post("/add")
async def add_download(req: Request, url: str, fpath: str):
    try:
        fingerprint = req.app.state.dservice.add_download(url, fpath)
        return successify({"fingerprint": fingerprint, "message": "Download added."})
    except Exception as e:
        return errorify(e)

@DmanRouter.post("/resume/{fingerprint}")
async def resume_download(req: Request, fingerprint: str, background_tasks: BackgroundTasks):
    success, message = req.app.state.dservice.resume_download(fingerprint)
    if not success:
        return errorify("failed to resume download")
    background_tasks.add_task(req.app.state.dservice.download_file, fingerprint)
    return successify({"message": message})

@DmanRouter.post("/pause/{fingerprint}")
async def pause_download(req: Request, fingerprint: str):
    success, message = req.app.state.dservice.pause_download(fingerprint)
    if not success:
        return errorify("failed to pause download")
    return successify({"message": message})

@DmanRouter.post("/remove/{fingerprint}")
async def remove_download(req: Request, fingerprint: str):
    success, message = req.app.state.dservice.remove_download(fingerprint)
    if not success:
        return errorify("failed to remove download")
    return successify({"message": message})

@DmanRouter.get("/list")
async def list_downloads(req: Request):
    download_list = req.app.state.dservice.list_downloads()
    return successify(download_list)

@DmanRouter.get("/status/{fingerprint}")
async def get_status(req: Request, fingerprint: str):
    status = req.app.state.dservice.get_status(fingerprint)
    if not status:
        return errorify("failed to get fingerprint status")
    return successify(DownloadStatusResponse(**status).model_dump())
