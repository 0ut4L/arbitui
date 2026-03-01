import asyncio
import platform
import zipfile
from asyncio.subprocess import Process
from asyncio.taskgroups import TaskGroup
from pathlib import Path
from typing import Optional

import aiohttp
from loguru import logger

from settings import settings

RELEASES_URL = "https://api.github.com/repos/0ut4L/rates-scope/releases"


def get_platform() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "x86_64-apple-darwin"
    elif system == "linux":
        return "x86_64-pc-linux"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


async def get_latest_release() -> Optional[dict]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(RELEASES_URL) as rsp:
                rsp.raise_for_status()
                releases = await rsp.json()
                if releases:
                    return releases[0]
                return None
    except Exception as e:
        logger.error(f"Failed to fetch releases: {e}")
        return None


async def download_binary(binary_dir: Path) -> bool:
    try:
        release = await get_latest_release()
        if not release:
            logger.error("No releases found")
            return False

        platform_id = get_platform()
        asset_name = f"rates-lib-graal-native-{platform_id}.zip"

        asset = next(
            (a for a in release.get("assets", []) if a["name"] == asset_name), None
        )

        if not asset:
            logger.error(f"No binary found for platform: {platform_id}")
            return False

        logger.info(f"Downloading {asset_name}...")

        binary_dir.mkdir(parents=True, exist_ok=True)

        download_url = asset["browser_download_url"]
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as rsp:
                rsp.raise_for_status()
                zip_path = binary_dir / asset_name
                with open(zip_path, "wb") as f:
                    async for chunk in rsp.content.iter_chunked(8192):
                        f.write(chunk)

        logger.info(f"Extracting {asset_name}...")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(binary_dir)

        zip_path.unlink()

        return True
    except Exception as e:
        logger.error(f"Failed to download binary: {e}")
        return False


async def ensure_binary(binary_path: Path) -> bool:
    if binary_path.exists():
        logger.info(f"Using cached binary at {binary_path}")
        return True

    logger.info("Binary not found, downloading...")
    print(binary_path)
    return await download_binary(binary_path.parents[0])


async def launch_binary(binary_dir: Path, binary: str):
    binary_path = binary_dir / binary

    if not await ensure_binary(binary_path):
        raise RuntimeError("Failed to obtain rates-scope binary")

    if binary_path.exists():
        binary_path.chmod(0o755)
        logger.info(f"Binary installed at {binary_path}")
    else:
        logger.error("Binary not found after extraction")
        raise

    logger.info(f"Launching {binary_path}")

    try:
        process = await asyncio.create_subprocess_exec(
            str(binary_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        return process
    except Exception as e:
        logger.error(f"Failed to launch binary: {e}")
        raise


if __name__ == "__main__":

    async def log(proc: Process):
        logs_dir = settings.home / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        with open(settings.home / "logs" / f"json-rpc-{proc.pid}.txt", "a") as f:
            while True:
                if stdout := proc.stdout:
                    bytes = await stdout.readline()
                    if not bytes:  # EOF
                        break
                    line = bytes.decode("utf-8").rstrip()
                    f.write(line + "\n")
                    f.flush()

    async def stop(proc: Process):
        await asyncio.sleep(3)
        logger.info(f"terminating process with PID: {proc.pid}")
        proc.kill()

    async def run():
        proc = await launch_binary(settings.home / "bin", "json-rpc")
        logger.info(f"json-rpc process launched with PID: {proc.pid}")
        async with TaskGroup() as tg:
            tg.create_task(log(proc))
            tg.create_task(stop(proc))
        await log(proc)
        return_code = await proc.wait()
        logger.info(f"process exited with return code {return_code}")

    asyncio.run(run())
