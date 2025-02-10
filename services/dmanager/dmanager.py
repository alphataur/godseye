import asyncio
import aiohttp
import hashlib
import time
import os
from .database import DownloadStatus, db
import datetime













class DownloadService:
    def __init__(self):
        self.download_tasks = {} # fingerprint -> task
        self.DDIR = "/home/oem/Downloads"

    def _process_fpath(self, fpath, fingerprint):
        """Processes the given file path based on its type and existence,
        and returns a modified path.
        """
    
        if not os.path.isabs(fpath):
            fpath = os.path.join(self.DDIR, fpath)
    
            if os.path.exists(fpath):
                root, ext = os.path.splitext(fpath)
                new_fpath = os.path.join(self.DDIR, fingerprint + "." + ext)
                os.rename(fpath, new_fpath)
                return new_fpath
            else:
                return fpath
        else:
            if not os.path.exists(fpath):
                dir_name = os.path.dirname(fpath)
                if os.path.exists(dir_name):
                    return fpath
                else:
                    return fpath
            elif os.path.isdir(fpath):
                root, ext = os.path.splitext(fpath)
                return os.path.join(fpath, fingerprint + "." + ext)
            else:
                return fpath


    def generate_fingerprint(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def add_download(self, url: str, fpath: str):
        fingerprint = self.generate_fingerprint(url)
        try:
            #process fpath
            fpath = self._process_fpath(fpath, fingerprint)
            DownloadStatus.create(fingerprint=fingerprint, url=url, fpath=fpath)
        except Exception as e:
            return "some e"
        return fingerprint

    async def download_file(self, fingerprint: str):
        try:
            download_status = DownloadStatus.get(DownloadStatus.fingerprint == fingerprint)
        except DownloadStatus.DoesNotExist:
            print(f"ERROR: Download with fingerprint {fingerprint} not found")
            return
        
        url = download_status.url
        fpath = download_status.fpath
        offset = download_status.offset
        is_paused = download_status.is_paused

        async with aiohttp.ClientSession() as session:
            headers = {'Range': f'bytes={offset}-'} if offset > 0 else {}
            start_time = time.time()
            last_update_time = start_time
            chunk_size = 8192 # 8KB chunk

            try:
                async with session.get(url, headers=headers) as response:
                    if response.status in [200, 206]:
                        total_length = int(response.headers.get('Content-Length', 0))
                        if response.status == 206:  # Partial content
                            content_range = response.headers.get('Content-Range')
                            if content_range:
                                try:
                                    start, end, total = self._parse_content_range(content_range)
                                    total_length = total
                                except ValueError:
                                    print(f"ERROR: Could not parse content range: {content_range}")
                                    return

                        download_status.length = total_length
                        
                        # Handle file appending for resume
                        mode = 'ab' if offset > 0 else 'wb'
                        with open(fpath, mode) as f:
                            async for chunk in response.content.iter_chunked(chunk_size):
                                if download_status.is_paused:
                                    print(f"Download {fingerprint} paused.")
                                    return  # Stop the download loop

                                if DownloadStatus.get(DownloadStatus.fingerprint == fingerprint).is_removed:
                                    print(f"Download {fingerprint} removed.")
                                    try:
                                        os.remove(fpath)  # Remove the incomplete file
                                    except FileNotFoundError:
                                        pass # Already removed
                                    return

                                f.write(chunk)
                                offset += len(chunk)
                                now = time.time()
                                elapsed = now - start_time
                                time_since_last_update = now - last_update_time
                                if time_since_last_update >= 0.5:
                                    last_speed = len(chunk) / time_since_last_update
                                    download_status.offset = offset
                                    download_status.elapsed = elapsed
                                    download_status.last_speed = last_speed
                                    download_status.updated_at = datetime.datetime.now()
                                    download_status.save()
                                    last_update_time = now

                        print(f"Download {fingerprint} complete.")
                    else:
                        print(f"ERROR: Download {fingerprint} failed with status {response.status}")
            except aiohttp.ClientError as e:
                print(f"ERROR: aiohttp error during download {fingerprint}: {e}")
            except Exception as e:
                print(f"ERROR: Unexpected error during download {fingerprint}: {e}")
            finally:
                download_status.updated_at = datetime.datetime.now()
                download_status.save()

    def resume_download(self, fingerprint: str):
        try:
            download_status = DownloadStatus.get(DownloadStatus.fingerprint == fingerprint)
            if download_status.is_removed:
                return False, "Download has been removed."
            download_status.is_paused = False
            download_status.save()
            task = asyncio.create_task(self.download_file(fingerprint))
            self.download_tasks[fingerprint] = task
            return True, "Download resumed"
        except DownloadStatus.DoesNotExist:
            return False, "Download not found."

    def pause_download(self, fingerprint: str):
        try:
            download_status = DownloadStatus.get(DownloadStatus.fingerprint == fingerprint)
            download_status.is_paused = True
            download_status.save()
            # No need to explicitly cancel the task, the download_file function checks is_paused
            return True, "Download paused."
        except DownloadStatus.DoesNotExist:
            return False, "Download not found."

    def remove_download(self, fingerprint: str):
        try:
            download_status = DownloadStatus.get(DownloadStatus.fingerprint == fingerprint)
            download_status.is_removed = True
            download_status.save()

            # attempt to delete the file.
            try:
                os.remove(download_status.fpath)
            except FileNotFoundError:
                pass # already deleted
            return True, "Download removed."
        except DownloadStatus.DoesNotExist:
            return False, "Download not found."

    def list_downloads(self):
        return [dl.fingerprint for dl in DownloadStatus.select()]

    def get_status(self, fingerprint: str):
        try:
            download_status = DownloadStatus.get(DownloadStatus.fingerprint == fingerprint)
            return {
                "fpath": download_status.fpath,
                "url": download_status.url,
                "fingerprint": download_status.fingerprint,
                "elapsed": download_status.elapsed,
                "offset": download_status.offset,
                "length": download_status.length,
                "last_speed": download_status.last_speed,
                "is_paused": download_status.is_paused,
                "is_removed": download_status.is_removed,
            }
        except DownloadStatus.DoesNotExist:
            return None

    def _parse_content_range(self, content_range):
        """Parses the Content-Range header."""
        # Example: bytes 1024-2047/2048
        try:
            range_spec, total_length = content_range.split('/')
            start_end = range_spec.split(' ')[1]  # Remove 'bytes ' prefix
            start, end = map(int, start_end.split('-'))
            total_length = int(total_length)
            return start, end, total_length
        except ValueError:
            raise ValueError("Invalid Content-Range format")

