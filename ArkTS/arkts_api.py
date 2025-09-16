import asyncio
import logging
import os
import pickle
import re
import shutil
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union
from urllib.parse import quote, unquote

import ohre
import ohre.misc.utils as oh_utils
from mcp.shared.exceptions import McpError
from ohre.abcre.dis.AsmMethod import AsmMethod
from ohre.abcre.dis.DisFile import DisFile
from ohre.abcre.dis.PandaReverser import PandaReverser, generate_content
from ohre.core.oh_app import oh_app
from ohre.core.oh_hap import oh_hap
from pydantic import AnyUrl, BaseModel, Field, FileUrl

ohre.set_log_print(False)


VULMCP_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARK_DISASM = os.path.join(VULMCP_ROOT_PATH, "tools", "ark_disasm")
TMP_HAP_EXTRACT = os.path.join(VULMCP_ROOT_PATH, "tmp_hap_extract")
# load it by default everytime, if it NOT exists, load it from DEFAULT_HAP_PATH or in_path
LOCAL_DEFAULT_PANDARE_PKL = os.path.join(VULMCP_ROOT_PATH, "main_pandare.pkl")
DEFAULT_HAP_PATH = os.path.join(VULMCP_ROOT_PATH, "main.hap")  # load it by default everytime
PANDA_RE_G: PandaReverser | None = None
OH_APP_OR_HAP_G: Union[oh_hap, oh_app] = None


module_method_name_l: List[str] | None = None

VULMCP_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr
)
log_name = "ArkTS_API"
log_file = os.path.join(VULMCP_ROOT_PATH, log_name + ".log")
Log = logging.getLogger(log_name)
handle = RotatingFileHandler(log_file, mode="a", maxBytes=50 * 1024 * 1024,
                             backupCount=10, encoding="utf-8", delay=0)
handle.setLevel(logging.INFO)
handle.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
Log.addHandler(handle)
Log.setLevel(logging.DEBUG)


def pickle_save_object(obj, filename: str):
    Log.info(f"pickle save: {filename}")
    with open(filename, "wb") as file:
        pickle.dump(obj, file)


def pickle_load_object(filename: str):
    Log.info(f"pickle load: {filename}")
    size = os.path.getsize(filename)
    if size == 0:
        return None
    with open(filename, "rb") as file:
        obj = pickle.load(file)
    return obj


def _disasm(in_path: str = DEFAULT_HAP_PATH, USE_LOCAL_PICKLE: bool = False):
    global PANDA_RE_G, OH_APP_OR_HAP_G
    Log.info(f"disasm: in_path {in_path} USE_LOCAL_PICKLE {USE_LOCAL_PICKLE}")
    try:
        if USE_LOCAL_PICKLE and os.path.isfile(LOCAL_DEFAULT_PANDARE_PKL):
            panda_re: PandaReverser = pickle_load_object(LOCAL_DEFAULT_PANDARE_PKL)
            if os.path.isfile(DEFAULT_HAP_PATH):
                temp: Union[oh_hap, oh_app] = oh_hap(DEFAULT_HAP_PATH)
                OH_APP_OR_HAP_G = temp
            else:
                Log.error(f"oh app or hap not exists: {DEFAULT_HAP_PATH} not exists")
            if isinstance(panda_re, PandaReverser):
                Log.info(f"panda_re load succ: from {LOCAL_DEFAULT_PANDARE_PKL}")
                PANDA_RE_G = panda_re
                return panda_re
            else:
                Log.info(f"panda_re load fail: from {LOCAL_DEFAULT_PANDARE_PKL}")
    except Exception as e:
        Log.error(f"load PandaReverser from pickle file failed, reverse it now...| exception: {e}")
    if (in_path.endswith(".dis") and os.path.isfile(in_path)):
        dis_file: DisFile = DisFile(in_path)
        Log.warning(f"hap file is better!")
    elif (in_path.endswith(".hap") and os.path.isfile(in_path)):
        hhap = oh_hap(in_path)
        path_in = Path(in_path).resolve(strict=False)
        path_default = Path(DEFAULT_HAP_PATH).resolve(strict=False)
        if os.path.exists(path_default) and not os.path.samefile(path_in, path_default):
            os.remove(path_default)
            shutil.copy2(in_path, path_default)
        OH_APP_OR_HAP_G = hhap
        hhap.extract_all_to(TMP_HAP_EXTRACT)
        abc_file = os.path.join(TMP_HAP_EXTRACT, "ets", "modules.abc")
        dis_file_name = f"{os.path.splitext(os.path.basename(in_path))[0]}.abc.dis"  # os.path.splitext(file_name)[0]
        result = subprocess.run([ARK_DISASM, abc_file, dis_file_name], capture_output=True, text=True)
        dis_file: DisFile = DisFile(dis_file_name)
    ohre.set_log_print(False)
    Log.info(f"disasm: start reverse with dis_file {dis_file}")
    panda_re: PandaReverser = PandaReverser(dis_file)
    panda_re.trans_lift_all_method(DEBUG_LV=0)
    panda_re.module_analysis_algorithms()
    pickle_save_object(panda_re, LOCAL_DEFAULT_PANDARE_PKL)
    PANDA_RE_G = panda_re
    return panda_re


def arkts_init():
    start_time = time.time()
    global PANDA_RE_G
    if PANDA_RE_G is None:
        PANDA_RE_G = _disasm(DEFAULT_HAP_PATH, True)
    OUT_FNAME = os.path.join(VULMCP_ROOT_PATH, "main.pa")
    with open(OUT_FNAME, "w", buffering=4 * 1024 * 1024) as file:
        for chunk in generate_content(PANDA_RE_G, start_time):
            file.write(chunk)
    return PANDA_RE_G


def get_all_module_method() -> List[str]:
    global PANDA_RE_G, module_method_name_l
    Log.info(f"get_all_module_method called")
    if PANDA_RE_G is None:
        arkts_init()
    panda_re = PANDA_RE_G
    if panda_re is None:
        raise ValueError("PANDA_RE_G is None, please init first")
    if module_method_name_l is None:
        ret = list()
        for module_name in sorted(panda_re.dis_file.methods.keys()):
            for methd_name in sorted(panda_re.dis_file.methods[module_name].keys()):
                ret.append(f"{module_name}.{methd_name}")
        module_method_name_l = ret
        return ret
    else:
        return module_method_name_l


async def get_module_method_panda_assembly_code(module_method_name: str) -> str:
    global PANDA_RE_G
    panda_re = PANDA_RE_G
    if panda_re is None:
        raise ValueError("PANDA_RE_G is None, please init first")
    module_name, method_name = oh_utils.split_to_module_method_name(module_method_name)
    if module_name not in panda_re.dis_file.methods or method_name not in panda_re.dis_file.methods[module_name]:
        return ""
    method: AsmMethod = panda_re.dis_file.methods[module_name][method_name]
    return f"ArkTS assembly code of module name={module_name}  method name={method_name}:\n" + method.str_for_LLM()


async def get_external_file_content(file_name: str) -> str:
    global OH_APP_OR_HAP_G
    raise NotImplementedError()


async def read_pa_by_url(uri: AnyUrl) -> list[str]:
    """get ArkTS assembly by uri like panda://module.method, wildcard matching supported."""
    Log.info(f"read-pa: uri: {uri} | host:{uri.host} path:{uri.path} {uri.port} {uri.query} {uri.unicode_string()}")
    VALUE_ERROR_MSG = f"Invalid resource path: {uri}. Valid resource URL example: panda://Index%26.%23%2A%23 (for specific match of Index&.#*# using URL encoding), panda://*module_name* (for wildcard matching of all methods in module/class named `module_name`). Check URL encoding or use wildcard matching if it still failed."
    res_pattern = uri.unicode_string()
    if len(res_pattern) <= 8 or not res_pattern.startswith("panda://"):
        raise McpError(VALUE_ERROR_MSG)
    res_pattern = res_pattern.lstrip("panda://")
    all_res = get_all_module_method()  # original module.method name, NOT quoted

    matched_res = []
    if unquote(res_pattern) in all_res:  # one-to-one match
        matched_res = [res_pattern]
    elif res_pattern in all_res:  # one-to-one match
        matched_res = [quote(res_pattern)]
    elif "*" in res_pattern:  # * match mode
        pattern = res_pattern.replace(".", r"\.").replace("*", ".*")
        pattern_unquoted = unquote(res_pattern).replace(".", r"\.").replace("*", ".*")
        regex = re.compile(f"^{pattern}$")  # re.compile(f"^{pattern}$")
        regex_unquoted = re.compile(f"^{pattern_unquoted}$")
        matched_res = [quote(res) for res in all_res if (regex.match(quote(res)) or regex.match(res))]
        matched_res.extend([quote(res) for res in all_res if (
            regex_unquoted.match(quote(res)) or regex_unquoted.match(res))])
        matched_res = sorted(list(set(matched_res)))

    if len(matched_res) == 0:  # It is better to return more unnecessary code than to return nothing
        matched_res = [quote(s) for s in all_res if (unquote(res_pattern) in s or res_pattern in s)]

    tasks = [get_module_method_panda_assembly_code(unquote(resource)) for resource in matched_res]
    contents: list[str] = await asyncio.gather(*tasks)
    if len(contents) == 0:
        raise McpError(
            VALUE_ERROR_MSG + f" Matched resource URL not exists. matched_res: {matched_res}. contents {contents}. res_pattern {res_pattern}")
    return contents

if __name__ == '__main__':
    ret = get_all_module_method()  # asyncio.run(
    Log.info(f"get_all_module_method: {len(ret)} {ret}")

    Log.info(quote("&vulwebview.src.main.ets.pages.Index&.#~@0>#aboutToAppear"))
