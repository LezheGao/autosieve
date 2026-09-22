#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用法:
    python autosieve.py [digits] [fdbuser] [msieve路径]
    python autosieve.py --digits 80 --type repunit
    python autosieve.py --type cunningham --base 3 --sign -1 --digits 100
    python autosieve.py --type prefix --prefix 123456789 --digits 90
    python autosieve.py --list-types
"""

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
FACTORDB_API = "https://factordb.com/api"

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
def _digit_limit(digits: int) -> int:
    """恰好 digits 位十进制数的最大值。"""
    return 10 ** digits - 1


def _largest_base_pow(base: int, limit: int):
    """返回 (n, base**n)，满足 base**n <= limit 且 n 最大。整数运算，无浮点误差。"""
    if base < 2:
        raise ValueError("底数必须 >= 2")
    n, p = 0, 1
    while p * base <= limit:
        p *= base
        n += 1
    return n, p


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


# ---------------- 数字生成器 ----------------
def gen_random(digits, **kw):
    """随机 digits 位奇数（默认）。"""
    return generate_odd(digits)


def gen_repunit(digits, **kw):
    """R_d = (10^d - 1) / 9，恰好 d 位，全 1。"""
    return (10 ** digits - 1) // 9


def gen_mersenne(digits, **kw):
    """2^p - 1，取最大 p 使结果不超过 digits 位。"""
    n, _ = _largest_base_pow(2, _digit_limit(digits))
    return 2 ** n - 1


def gen_fermat(digits, **kw):
    """2^(2^m) + 1，取最大 m 使结果不超过 digits 位。"""
    limit = _digit_limit(digits) - 1          # 需要 2^(2^m) <= limit
    k, _ = _largest_base_pow(2, limit)        # 2^k <= limit
    m = 0
    while 2 ** (m + 1) <= k:                  # 2^m <= k
        m += 1
    return 2 ** (2 ** m) + 1


def gen_cunningham(digits, base=2, sign=1, **kw):
    """b^n ± 1，取最大 n 使结果不超过 digits 位。"""
    base = int(base)
    sign = int(sign)
    if base < 2:
        raise ValueError("cunningham 底数必须 >= 2")
    if sign not in (-1, 1):
        raise ValueError("sign 必须是 +1 或 -1")
    limit = _digit_limit(digits)
    if sign == 1:
        n, _ = _largest_base_pow(base, limit - 1)   # b^n + 1 <= limit
        return base ** n + 1
    else:
        n, _ = _largest_base_pow(base, limit + 1)   # b^n - 1 <= limit
        return base ** n - 1


def gen_factorial(digits, sign=1, **kw):
    """n! ± 1，取最大 n 使结果不超过 digits 位。"""
    sign = int(sign)
    if sign not in (-1, 1):
        raise ValueError("sign 必须是 +1 或 -1")
    cap = _digit_limit(digits) - sign          # 需要 n! <= cap
    n, f = 1, 1
    while f * (n + 1) <= cap:
        n += 1
        f *= n
    return f + sign


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def gen_primorial(digits, sign=1, **kw):
    """p# ± 1，取最大素数 p 使结果不超过 digits 位。"""
    sign = int(sign)
    if sign not in (-1, 1):
        raise ValueError("sign 必须是 +1 或 -1")
    cap = _digit_limit(digits) - sign
    p = 1
    n = 1
    while True:
        n += 1
        if not _is_prime(n):
            continue
        if p * n > cap:
            break
        p *= n
    return p + sign


def gen_sophie(digits, **kw):
    """x^4 + 4，取最大 x 使结果不超过 digits 位。
    注意：x^4 + 4 = (x^2 - 2x + 2)(x^2 + 2x + 2)，必可分解。"""
    cap = _digit_limit(digits) - 4
    if cap < 1:
        return 5
    x = 1
    while (x + 1) ** 4 <= cap:
        x += 1
    return x ** 4 + 4


def gen_prefix(digits, prefix="1", **kw):
    """以指定前缀开头的随机 digits 位数（前缀后补随机数字）。"""
    prefix = str(prefix)
    rest = digits - len(prefix)
    if rest < 0:
        raise ValueError(f"前缀 {prefix!r} 比 digits={digits} 还长")
    if rest == 0:
        return int(prefix)
    suffix = "".join(random.choices("0123456789", k=rest))
    return int(prefix + suffix)


GENERATORS = {
    "random":     gen_random,
    "repunit":    gen_repunit,
    "mersenne":   gen_mersenne,
    "fermat":     gen_fermat,
    "cunningham": gen_cunningham,
    "factorial":  gen_factorial,
    "primorial":  gen_primorial,
    "sophie":     gen_sophie,
    "prefix":     gen_prefix,
}

GENERATOR_HELP = {
    "random":     "随机 digits 位奇数（默认）",
    "repunit":    "R_d = (10^d - 1) / 9，恰好 d 位全 1",
    "mersenne":   "2^p - 1，取最大 p 使不超过 digits 位",
    "fermat":     "2^(2^m) + 1，取最大 m 使不超过 digits 位",
    "cunningham": "b^n ± 1，参数 --base B（默认 2）、--sign ±1（默认 +1）",
    "factorial":  "n! ± 1，参数 --sign ±1（默认 +1）",
    "primorial":  "p# ± 1，参数 --sign ±1（默认 +1）",
    "sophie":     "x^4 + 4 = (x^2-2x+2)(x^2+2x+2)，必可分解",
    "prefix":     "以 --prefix 开头的随机 digits 位数（默认前缀 1）",
}


def generate_number(digits: int, gen_type: str, extra: dict) -> int:
    fn = GENERATORS.get(gen_type)
    if fn is None:
        raise ValueError(
            f"未知生成类型 {gen_type!r}，可用：{', '.join(sorted(GENERATORS))}"
        )
    n = fn(digits, **extra)
    if n >= 10 ** digits:
        raise RuntimeError(
            f"生成器 {gen_type} 产出 {n}，超过 {digits} 位，请检查参数"
        )
    if n < 2:
        raise RuntimeError(f"生成器 {gen_type} 产出非法值 {n}（< 2）")
    return n


# ---------------- FactorDB / msieve ----------------
def query_factordb(number: int, fdbuser: str):
    """GET https://factordb.com/api?query=<number>
    返回 (ok, status, raw)：
        ok     查询是否成功执行
        status "FF" / "C" / "U" / "P" / "PRP" / ... ；解析失败为 None
        raw    curl 原始输出
    """
    url = f"{FACTORDB_API}?query={number}"
    cmd = [
        CURL_PATH,
        "-s",
        "-X", "GET",
        "--cookie", f"fdbuser={fdbuser}",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        log(f"[!] FactorDB 查询异常：{e!r}")
        return False, None, ""

    raw = result.stdout.strip()
    status = None
    m = re.search(r'"status"\s*:\s*"([^"]+)"', raw)
    if m:
        status = m.group(1)
    return True, status, raw


def _msieve_log_paths(cwd):
    paths = []
    if cwd:
        paths.append(os.path.join(cwd, "msieve.log"))
    paths.append(os.path.join(os.getcwd(), "msieve.log"))
    return paths


def run_msieve(number: int):
    """调用 msieve -v -t N <number>，返回 (verified_factors, raw_output)。"""
    cwd = os.path.dirname(MSIEVE_PATH) or None
    log_paths = _msieve_log_paths(cwd)

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
def print_help():
    print(__doc__ or "autosieve.py")
    print("可用生成器（--type）：")
    for name in sorted(GENERATORS):
        print(f"  {name:12s}  {GENERATOR_HELP.get(name, '')}")


def parse_args(argv):
    digits = DEFAULT_DIGITS
    fdbuser = DEFAULT_FDBUSER
    msieve = DEFAULT_MSIEVE_PATH
    gen_type = "random"
    extra = {}

    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]

        if a in ("--help", "-h"):
            print_help()
            sys.exit(0)
        if a == "--list-types":
            print("可用生成器：" + ", ".join(sorted(GENERATORS)))
            sys.exit(0)

        if a.startswith("--") and "=" in a:
            key, _, value = a[2:].partition("=")
            inline = True
        elif a.startswith("--"):
            key = a[2:]
            value = None
            inline = False
        else:
            positional.append(a)
            i += 1
            continue

        if not inline:
            if i + 1 >= len(argv):
                raise SystemExit(f"--{key} 需要一个值")
            value = argv[i + 1]
            i += 1

        if key == "msieve":
            msieve = value
        elif key == "digits":
            digits = int(value)
        elif key == "fdbuser":
            fdbuser = value
        elif key == "type":
            gen_type = value
        elif key == "base":
            extra["base"] = int(value)
        elif key == "sign":
            extra["sign"] = int(value)
        elif key == "prefix":
            extra["prefix"] = value
        else:
            raise SystemExit(f"未知参数 --{key}（试试 --help）")

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

    return digits, fdbuser, msieve, gen_type, extra


# ---------------- 主流程 ----------------
def main():
    global MSIEVE_PATH

    digits, fdbuser, msieve, gen_type, extra = parse_args(sys.argv[1:])
    MSIEVE_PATH = msieve

    if gen_type not in GENERATORS:
        log(f"[!] 未知生成类型 {gen_type!r}，可用：{', '.join(sorted(GENERATORS))}")
        sys.exit(1)

    log("=" * 70)
    log(f"[*] 启动：digits={digits}, type={gen_type}, 参数={extra}")
    log(f"[*] fdbuser={fdbuser}")
    log(f"[*] msieve ：{MSIEVE_PATH} -v -t {MSIEVE_THREADS}")
    log(f"[*] curl   ：{CURL_PATH}")
    log(f"[*] 日志   ：{LOG_FILE}")
    log("[*] Ctrl+C 退出")
    log(f"[*] 生成器说明：{GENERATOR_HELP.get(gen_type, '')}")
    log("=" * 70)

    while True:
        try:
            number = generate_number(digits, gen_type, extra)
            log(f"[*] 生成（type={gen_type}）：{number}")
            if number % 2 == 0:
                log("[d] 注意：本次为偶数，msieve 会先提取因子 2")

            # ---- 1) 分解前先查 FactorDB ----
            ok, status, raw = query_factordb(number, fdbuser)
            log(f"[*] FactorDB 查询：ok={ok} status={status} raw={raw!r}")
            if ok and status == "FF":
                log("[*] 该数在 FactorDB 已完全分解（FF），跳过本次")
                time.sleep(1)
                continue

            # ---- 2) msieve 分解 ----
            factors, _ = run_msieve(number)

            if not factors:
                log("[!] 本次未提取到有效因子")
            else:
                sorted_factors = sorted(factors, reverse=True)   # 倒序
                log(f"[*] 有效因子（已校验，从大到小）：{sorted_factors}")
                for factor in sorted_factors:
                    code, out, err = report_factor(number, factor, fdbuser)
                    log(f"[*] 上报 number={number} factor={factor} -> rc={code} | resp={out!r}")
                    if err:
                        log(f"    stderr: {err}")
                    # ---- 3) 已完全分解就不再上报剩余因子 ----
                    if "Already fully factored" in out:
                        log("[*] FactorDB 回报 Already fully factored，停止上报剩余因子")
                        break

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
