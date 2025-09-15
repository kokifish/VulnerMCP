import os
import subprocess
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union
from urllib.parse import quote, unquote

import ohre
import ohre.misc.utils as oh_utils
from ohre.abcre.dis.AsmMethod import AsmMethod
from ohre.abcre.dis.DisFile import DisFile
from ohre.abcre.dis.PandaReverser import PandaReverser
from ohre.core import oh_app, oh_hap
import pickle

ohre.set_log_print(False)
ARK_DISASM = "tools/ark_disasm"
TMP_HAP_EXTRACT = "tmp_hap_extract"

VULMCP_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DEFAULT_PANDARE_PKL = os.path.join(VULMCP_ROOT_PATH, "main.pkl")
panda_re_global: PandaReverser | None = None
module_methd_name_l: List[str] | None = None


def pickle_save_object(obj, filename: str):
    with open(filename, "wb") as file:
        pickle.dump(obj, file)


def pickle_load_object(filename: str):
    size = os.path.getsize(filename)
    if size == 0:
        return None
    with open(filename, "rb") as file:
        obj = pickle.load(file)
    return obj


def disasm(in_path: str = os.path.join(VULMCP_ROOT_PATH, "main.dis"), USE_LOCAL_PICKLE: bool = True):
    global panda_re_global
    try:
        if USE_LOCAL_PICKLE and os.path.isfile(LOCAL_DEFAULT_PANDARE_PKL):
            panda_re: PandaReverser = pickle_load_object(LOCAL_DEFAULT_PANDARE_PKL)
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
    pickle_save_object(panda_re, LOCAL_DEFAULT_PANDARE_PKL)
    panda_re_global = panda_re


def get_all_module_method() -> List[str]:
    global panda_re_global, module_methd_name_l
    if panda_re_global is None:
        disasm()
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


if __name__ == "__main__":
    disasm()
    ret = get_all_module_method()
    print(f"get_all_module_method: {len(ret)} {ret}")

    print(quote("&vulwebview.src.main.ets.pages.Index&.#~@0>#aboutToAppear"))
