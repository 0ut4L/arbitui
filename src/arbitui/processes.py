import asyncio
from asyncio.subprocess import Process
from typing import List

from loguru import logger

from arbitui import utils
from arbitui.settings import settings


async def launch_native_image() -> Process:
    binary_path = settings.home / "bin" / "json-rpc"

    if not await utils.ensure_binary(binary_path):
        raise RuntimeError("Failed to obtain rates-scope binary")

    if binary_path.exists():
        binary_path.chmod(0o755)
        logger.info(f"Binary installed at {binary_path}")
    else:
        logger.error("Binary not found after extraction")
        raise

    logger.info(f"Launching {binary_path}")

    try:
        proc = await asyncio.create_subprocess_exec(
            str(binary_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        logger.info(f"native image with PID {proc.pid}")
        return proc
    except Exception as e:
        logger.error(f"Failed to launch native image: {e}")
        raise


async def launch_server() -> Process:
    logger.info("starting server ...")
    try:
        proc = await asyncio.create_subprocess_exec(
            "uvicorn",
            "arbitui.server:app",
            "--timeout-graceful-shutdown",
            "0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        logger.info(f"server process with PID {proc.pid}")
        return proc
    except Exception as e:
        logger.error(f"Failed to launch server: {e}")
        raise


async def launch_processes() -> List[Process]:
    proc0 = await launch_server()
    proc1 = await launch_native_image()
    await asyncio.sleep(3)
    return [proc0, proc1]


if __name__ == "__main__":

    async def dump_logs(proc: Process):
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
        # await launch_server()
        # proc = await launch_native_image()
        # async with TaskGroup() as tg:
        #     tg.create_task(dump_logs(proc))
        #     tg.create_task(stop(proc))
        # await dump_logs(proc)
        # return_code = await proc.wait()
        # logger.info(f"process exited with return code {return_code}")

        await launch_processes()
        logger.info("processes started")

    asyncio.run(run())
