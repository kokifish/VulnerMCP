import asyncio
import logging
import os
import pickle
import re
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union
from urllib.parse import quote, unquote

import ohre
import ohre.misc.utils as oh_utils
from mcp.server.fastmcp.exceptions import ResourceError
from ohre.abcre.dis.AsmMethod import AsmMethod
from ohre.abcre.dis.DisFile import DisFile
from ohre.abcre.dis.PandaReverser import PandaReverser
from ohre.core import oh_app, oh_hap
from pydantic import AnyUrl, BaseModel, Field, FileUrl

ohre.set_log_print(False)
ARK_DISASM = "tools/ark_disasm"
TMP_HAP_EXTRACT = "tmp_hap_extract"

VULMCP_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DEFAULT_PANDARE_PKL = os.path.join(VULMCP_ROOT_PATH, "main.pkl")
panda_re_global: PandaReverser | None = None
module_methd_name_l: List[str] | None = None

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


async def pickle_save_object(obj, filename: str):
    with open(filename, "wb") as file:
        pickle.dump(obj, file)


async def pickle_load_object(filename: str):
    size = os.path.getsize(filename)
    if size == 0:
        return None
    with open(filename, "rb") as file:
        obj = pickle.load(file)
    return obj


async def disasm(in_path: str = os.path.join(VULMCP_ROOT_PATH, "main.dis"), USE_LOCAL_PICKLE: bool = True):
    global panda_re_global
    try:
        if USE_LOCAL_PICKLE and os.path.isfile(LOCAL_DEFAULT_PANDARE_PKL):
            panda_re: PandaReverser = await pickle_load_object(LOCAL_DEFAULT_PANDARE_PKL)
            if isinstance(panda_re, PandaReverser):
                panda_re_global = panda_re
                return
    except Exception as e:
        print(f"load PandaReverser from pickle file failed, reverse it now...| exception: {e}")
    if (in_path.endswith(".dis")):
        dis_file: DisFile = DisFile(in_path)
    elif (in_path.endswith(".hap")):
        hhap = oh_hap.oh_hap(in_path)
        hhap.extract_all_to(TMP_HAP_EXTRACT)
        abc_file = os.path.join(TMP_HAP_EXTRACT, "ets", "modules.abc")
        dis_file_name = f"{os.path.splitext(os.path.basename(in_path))[0]}.abc.dis"  # os.path.splitext(file_name)[0]
        result = subprocess.run([ARK_DISASM, abc_file, dis_file_name], capture_output=True, text=True)
        dis_file: DisFile = DisFile(dis_file_name)
    ohre.set_log_print(False)
    panda_re: PandaReverser = PandaReverser(dis_file)
    panda_re.trans_lift_all_method(DEBUG_LV=0)
    panda_re.module_analysis_algorithms()
    await pickle_save_object(panda_re, LOCAL_DEFAULT_PANDARE_PKL)
    panda_re_global = panda_re


async def get_all_module_method() -> List[str]:
    global panda_re_global, module_methd_name_l
    if panda_re_global is None:
        await disasm()
    panda_re = panda_re_global
    if panda_re is None:
        raise ValueError("panda_re_global is None, please run disasm first")
    if module_methd_name_l is None:
        ret = list()
        for module_name in sorted(panda_re.dis_file.methods.keys()):
            for methd_name in sorted(panda_re.dis_file.methods[module_name].keys()):
                ret.append(f"{module_name}.{methd_name}")
        module_methd_name_l = ret
        return ret
    else:
        return module_methd_name_l


async def get_module_method_panda_assembly_code(module_method_name: str) -> str:
    global panda_re_global
    panda_re = panda_re_global
    if panda_re is None:
        raise ValueError("panda_re_global is None, please run disasm first")
    module_name, method_name = oh_utils.split_to_module_method_name(module_method_name)
    if module_name not in panda_re.dis_file.methods or method_name not in panda_re.dis_file.methods[module_name]:
        return ""
    method: AsmMethod = panda_re.dis_file.methods[module_name][method_name]
    return f"ArkTS assembly code of: module name: {module_name}  method name: {method_name}\n" + method.str_for_LLM()


async def get_external_file_content(file_name: str) -> str:
    global panda_re_global
    raise NotImplementedError()


async def read_pa_by_url(uri: AnyUrl) -> list[str]:
    """get ArkTS assembly by uri like panda://module.method, wildcard matching supported."""
    Log.info(f"read-pa: uri: {uri} | host:{uri.host} path:{uri.path} {uri.port} {uri.query} {uri.unicode_string()}")
    VALUE_ERROR_MSG = f"Invalid resource path: {uri}. Valid resource URL example: panda://Index%26.%23%2A%23 (for specific match of Index&.#*#), panda://*module_name* (for wildcard matching of all methods in module/class named `module_name`). Check URL encoding or use wildcard matching if it still failed."
    res_pattern = uri.unicode_string()
    if len(res_pattern) <= 8 or not res_pattern.startswith("panda://"):
        raise ResourceError(VALUE_ERROR_MSG)
    res_pattern = res_pattern.lstrip("panda://")
    all_res = await get_all_module_method()  # original module.method name, NOT quoted

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

    if len(matched_res) == 0:  # It is better to return more unnecessary code than to return nothing
        matched_res = [quote(s) for s in all_res if (unquote(res_pattern) in s or res_pattern in s)]

    tasks = [get_module_method_panda_assembly_code(unquote(resource)) for resource in matched_res]
    contents: list[str] = await asyncio.gather(*tasks)
    if len(contents) == 0:
        raise ResourceError(
            VALUE_ERROR_MSG + f" Matched resource URL not exists. matched_res: {matched_res}. contents {contents}. res_pattern {res_pattern}")
    return contents

if __name__ == "__main__":
    disasm()
    ret = get_all_module_method()
    print(f"get_all_module_method: {len(ret)} {ret}")

    print(quote("&vulwebview.src.main.ets.pages.Index&.#~@0>#aboutToAppear"))
