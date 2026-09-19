#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import random
import tempfile
import subprocess
from datetime import datetime

# ---------------- 默认配置 ----------------
DEFAULT_DIGITS = 80
DEFAULT_FDBUSER = ""
DEFAULT_MSIEVE_PATH = r"D:\MSIEVE\msieve.exe"
MSIEVE_THREADS = 5
CURL_PATH = "curl.exe"
FACTORDB_URL = "https://factordb.com/reportfactor.php"

# 全局变量（在 main 里根据参数覆盖）
MSIEVE_PATH = DEFAULT_MSIEVE_PATH

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt")
_log_fh = open(LOG_FILE, "a", encoding="utf-8", buffering=1)


def log(msg: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        _log_fh.write(line + "\n")
        _log_fh.flush()
    except Exception:
        pass


# ---------------- 工具函数 ----------------
def generate_odd(digits: int) -> int:
    if digits < 1:
        raise ValueError("位数必须 >= 1")
    low = 1 if digits == 1 else 10 ** (digits - 1)
    high = 10 ** digits - 1
    n = random.randrange(low, high + 1)
    if n % 2 == 0:
        n += 1
        if n > high:
            n -= 2
    return n


def _msieve_log_paths(cwd):
    paths = []
    if cwd:
        paths.append(os.path.join(cwd, "msieve.log"))
    paths.append(os.path.join(os.getcwd(), "msieve.log"))
    return paths


def run_msieve(number: int):
    """调用 msieve -v -t N <number>，返回 (verified_factors, raw_output)"""
    cwd = os.path.dirname(MSIEVE_PATH) or None
    log_paths = _msieve_log_paths(cwd)

    # 预先删除旧 msieve.log，避免历史因子污染
    for lp in log_paths:
        if os.path.exists(lp):
            try:
                os.remove(lp)
            except OSError as e:
                log(f"[d] 无法删除旧日志 {lp}: {e}")

    fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="msieve_out_")
    os.close(fd)

    try:
        cmd = [MSIEVE_PATH, "-v", "-t", str(MSIEVE_THREADS), str(number)]
        log(f"[d] 执行: {' '.join(cmd)}  (cwd={cwd})")

        with open(out_path, "w", encoding="utf-8", errors="ignore") as fout:
            proc = subprocess.run(
                cmd, stdout=fout, stderr=subprocess.STDOUT, cwd=cwd
            )

        with open(out_path, "r", encoding="utf-8", errors="ignore") as fin:
            stdout_content = fin.read()

        log(f"[d] msieve returncode={proc.returncode}, stdout 长度={len(stdout_content)}")

        log_content = ""
        for lp in log_paths:
            if os.path.exists(lp):
                try:
                    with open(lp, "r", encoding="utf-8", errors="ignore") as fl:
                        log_content += fl.read()
                except Exception as e:
                    log(f"[d] 读取 {lp} 失败: {e}")

        full_output = stdout_content + ("\n" + log_content if log_content.strip() else "")

        if not full_output.strip():
            log("[!] msieve 无任何输出，请手动执行：")
            log(f'    "{MSIEVE_PATH}" -v -t {MSIEVE_THREADS} {number}')
        else:
            log("[d] msieve 原始输出：")
            for line in full_output.splitlines():
                log("    | " + line)

        # 解析因子
        candidates = set()
        for line in full_output.splitlines():
            m = re.search(r"factor:\s*(\d+)", line)
            if m:
                v = int(m.group(1))
                if v > 1:
                    candidates.add(v)
                continue
            m2 = re.search(r"\bp\w*\d*\s*=\s*(\d{4,})", line)
            if m2:
                v = int(m2.group(1))
                if v > 1:
                    candidates.add(v)

        # 校验整除
        verified = set()
        for f in candidates:
            if number % f == 0:
                verified.add(f)
            else:
                log(f"[!] 丢弃非因子 {f}（不能整除当前数字）")

        return verified, full_output
    finally:
        try:
            os.remove(out_path)
        except OSError:
            pass


def report_factor(number: int, factor: int, fdbuser: str):
    data = f"number={number}&factor={factor}"
    cmd = [
        CURL_PATH,
        "-s",
        "-X", "POST",
        "--cookie", f"fdbuser={fdbuser}",
        FACTORDB_URL,
        "-d", data,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------- 命令行解析 ----------------
def parse_args(argv):
    """
    位置参数（均可省略）：
      1) 位数          默认 80
      2) fdbuser       默认 为空字符串
      3) msieve 路径   默认 D:\\MSIEVE\\msieve.exe
    也支持命名参数：
      --msieve PATH   或   --msieve=PATH
      --digits N      或   --digits=N
      --fdbuser X     或   --fdbuser=X
    """
    digits = DEFAULT_DIGITS
    fdbuser = DEFAULT_FDBUSER
    msieve = DEFAULT_MSIEVE_PATH

    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--msieve":
            i += 1
            if i >= len(argv):
                raise SystemExit("--msieve 需要一个路径参数")
            msieve = argv[i]
        elif a.startswith("--msieve="):
            msieve = a.split("=", 1)[1]
        elif a == "--digits":
            i += 1
            if i >= len(argv):
                raise SystemExit("--digits 需要一个整数参数")
            digits = int(argv[i])
        elif a.startswith("--digits="):
            digits = int(a.split("=", 1)[1])
        elif a == "--fdbuser":
            i += 1
            if i >= len(argv):
                raise SystemExit("--fdbuser 需要一个值")
            fdbuser = argv[i]
        elif a.startswith("--fdbuser="):
            fdbuser = a.split("=", 1)[1]
        else:
            positional.append(a)
        i += 1

    if len(positional) >= 1:
        try:
            digits = int(positional[0])
        except ValueError:
            log(f"[!] 无效长度参数：{positional[0]}，使用默认 {DEFAULT_DIGITS}")
    if len(positional) >= 2:
        fdbuser = positional[1]
    if len(positional) >= 3:
        msieve = positional[2]
    if len(positional) > 3:
        log(f"[!] 多余参数被忽略：{positional[3:]}")

    return digits, fdbuser, msieve


# ---------------- 主流程 ----------------
def main():
    global MSIEVE_PATH

    digits, fdbuser, msieve = parse_args(sys.argv[1:])
    MSIEVE_PATH = msieve

    log("=" * 70)
    log(f"[*] 启动：长度={digits}, fdbuser={fdbuser}")
    log(f"[*] msieve：{MSIEVE_PATH} -v -t {MSIEVE_THREADS}")
    log(f"[*] curl  ：{CURL_PATH}")
    log(f"[*] 日志  ：{LOG_FILE}")
    log("[*] Ctrl+C 退出")
    log("[*] 用法：python 脚本.py [位数] [fdbuser] [msieve路径]")
    log("    或：python 脚本.py --digits 100 --fdbuser xxx --msieve D:\\MSIEVE\\msieve.exe")
    log("=" * 70)

    while True:
        try:
            number = generate_odd(digits)
            log(f"[*] 生成 {digits} 位奇数：{number}")

            factors, _ = run_msieve(number)

            if not factors:
                log("[!] 本次未提取到有效因子")
            else:
                log(f"[*] 有效因子（已校验）：{sorted(factors)}")
                for factor in sorted(factors):
                    code, out, err = report_factor(number, factor, fdbuser)
                    log(f"[*] 上报 number={number} factor={factor} -> rc={code} | resp={out!r}")
                    if err:
                        log(f"    stderr: {err}")

        except KeyboardInterrupt:
            log("[*] 用户中断，退出")
            break
        except Exception as e:
            log(f"[!] 异常：{e!r}")

        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            _log_fh.close()
        except Exception:
            pass
