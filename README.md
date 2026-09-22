# autosieve

> 基于 Windows、CURL 和 MSIEVE 的 FactorDB 自动提交系统

`autosieve` 是一个 Python 3 自动化脚本，用于循环生成指定长度的数字，调用 [MSIEVE](https://github.com/radii/msieve) 进行整数分解，提取有效因子，并通过 `curl` 将因子自动提交到 [FactorDB](https://factordb.com/)。

---

## 功能特性

- 支持 9 种数字生成器：`random`、`repunit`、`mersenne`、`fermat`、`cunningham`、`factorial`、`primorial`、`sophie`、`prefix`
- 自动生成不超过指定十进制位数的数字
- 分解前先查询 FactorDB API，若已完全分解则跳过
- 调用 `msieve` 进行整数分解
- 从 `msieve` 标准输出和 `msieve.log` 中解析因子
- 校验因子能否整除原数，过滤无效结果
- 因子按从大到小排序后通过 `curl` 提交到 FactorDB
- 若 FactorDB 返回 `Already fully factored`，停止上报剩余因子
- 支持命令行参数覆盖默认配置
- 自动记录运行日志到 `log.txt`
- 支持 `Ctrl+C` 安全退出
- 支持 `--help` 和 `--list-types`

---

## 工作流程

1. 根据 `--type` 选择生成器，生成不超过指定 `digits` 位的数字。
2. 若生成的数字为偶数，日志会提示 `msieve` 将先提取因子 2。
3. 调用 FactorDB API 查询该数状态：
   - 若状态为 `FF`（完全分解），跳过本轮。
4. 执行 `msieve -v -t 5 <number>` 进行分解。
5. 读取 `msieve` 输出和日志，解析 `factor:`、`pXX =` 等格式的因子。
6. 校验每个因子是否能整除原数。
7. 将有效因子按从大到小排序，逐个使用 `curl` 向 FactorDB 提交：
   ```text
   number=<原数>&factor=<因子>
   ```
8. 若 FactorDB 返回 `Already fully factored`，停止上报剩余因子。
9. 休眠 1 秒，继续下一轮。

---

## 环境要求

- **操作系统**：Windows（默认路径为 Windows 风格，其他系统需修改配置）
- **Python**：Python 3.6 或更高版本
- **MSIEVE**：已安装并可执行，默认路径为 `D:\MSIEVE\msieve.exe`
- **CURL**：`curl.exe` 已加入系统 `PATH`，或修改脚本中的 `CURL_PATH`

脚本仅使用 Python 标准库，无需额外安装第三方包。

---

## 安装与配置

1. 下载并安装 MSIEVE，确保 `msieve.exe` 可正常运行。
2. 确保 `curl.exe` 可在命令行中直接调用。
3. 将脚本保存为 `autosieve.py`。
4. 根据需要修改脚本顶部的默认配置：

```
DEFAULT_DIGITS = 80
DEFAULT_FDBUSER = ""
DEFAULT_MSIEVE_PATH = r"D:\MSIEVE\msieve.exe"
MSIEVE_THREADS = 5
CURL_PATH = "curl.exe"
FACTORDB_URL = "https://factordb.com/reportfactor.php"
FACTORDB_API = "https://factordb.com/api"
```

配置说明：

| 配置项 | 说明 | 默认值 |
|---|---|---|
| `DEFAULT_DIGITS` | 默认生成数字的十进制位数 | `80` |
| `DEFAULT_FDBUSER` | FactorDB 用户名 | `""` |
| `DEFAULT_MSIEVE_PATH` | `msieve.exe` 路径 | `D:\MSIEVE\msieve.exe` |
| `MSIEVE_THREADS` | MSIEVE 使用的线程数 | `5` |
| `CURL_PATH` | curl 可执行文件路径 | `curl.exe` |
| `FACTORDB_URL` | FactorDB 因子提交地址 | `https://factordb.com/reportfactor.php` |
| `FACTORDB_API` | FactorDB API 查询地址 | `https://factordb.com/api` |

---

## 使用方法

### 位置参数

```
python autosieve.py [位数] [fdbuser] [msieve路径]
```

示例：

```
python autosieve.py
```

使用默认配置：80 位、空 fdbuser、`D:\MSIEVE\msieve.exe`、随机奇数。

```
python autosieve.py 100
```

生成 100 位随机奇数。

```
python autosieve.py 100 myuser
```

生成 100 位随机奇数，并以 `myuser` 身份提交到 FactorDB。

```
python autosieve.py 100 myuser D:\MSIEVE\msieve.exe
```

指定完整参数。

### 命名参数

```
python autosieve.py --digits 100 --fdbuser myuser --msieve D:\MSIEVE\msieve.exe
```

也支持等号形式：

```
python autosieve.py --digits=100 --fdbuser=myuser --msieve=D:\MSIEVE\msieve.exe
```

### 选择生成器

```
python autosieve.py --digits 80 --type repunit
python autosieve.py --type cunningham --base 3 --sign -1 --digits 100
python autosieve.py --type prefix --prefix 123456789 --digits 90
python autosieve.py --list-types
```

### 参数说明

| 参数 | 说明 |
|---|---|
| `位数` / `--digits` | 生成数字的十进制位数，默认 `80` |
| `fdbuser` / `--fdbuser` | FactorDB 用户名，用于提交和查询时携带 cookie |
| `msieve路径` / `--msieve` | `msieve.exe` 的完整路径 |
| `--type` | 生成器类型，默认 `random` |
| `--base` | `cunningham` 生成器底数，默认 `2` |
| `--sign` | `cunningham` / `factorial` / `primorial` 的符号，`+1` 或 `-1`，默认 `+1` |
| `--prefix` | `prefix` 生成器的前缀，默认 `1` |
| `--list-types` | 列出所有可用生成器并退出 |
| `--help` / `-h` | 显示帮助并退出 |

位置参数和命名参数可以混用。命名参数先解析，位置参数后覆盖。

---

## 生成器列表

| 类型 | 说明 | 额外参数 |
|---|---|---|
| `random` | 随机 `digits` 位奇数（默认） | 无 |
| `repunit` | `R_d = (10^d - 1) / 9`，恰好 `d` 位全 1 | 无 |
| `mersenne` | `2^p - 1`，取最大 `p` 使结果不超过 `digits` 位 | 无 |
| `fermat` | `2^(2^m) + 1`，取最大 `m` 使结果不超过 `digits` 位 | 无 |
| `cunningham` | `b^n ± 1`，取最大 `n` 使结果不超过 `digits` 位 | `--base`、`--sign` |
| `factorial` | `n! ± 1`，取最大 `n` 使结果不超过 `digits` 位 | `--sign` |
| `primorial` | `p# ± 1`，取最大素数 `p` 使结果不超过 `digits` 位 | `--sign` |
| `sophie` | `x^4 + 4 = (x^2-2x+2)(x^2+2x+2)`，必可分解 | 无 |
| `prefix` | 以 `--prefix` 开头的随机 `digits` 位数 | `--prefix` |

使用 `--list-types` 可快速查看所有生成器名称。

---

## 日志

脚本会在同目录下生成 `log.txt`，以追加方式记录运行信息，包括：

- 启动配置
- 生成器类型与参数
- 生成的数字
- FactorDB 查询结果
- MSIEVE 执行命令
- MSIEVE 原始输出
- 解析到的因子
- 因子校验结果
- FactorDB 提交结果
- 异常信息

日志同时输出到控制台。

---

## 注意事项

1. **依赖外部程序**：必须正确安装和设置 `msieve` 和 `curl`等工具。
2. **默认路径为 Windows 风格**：Linux/macOS 下需要修改 `DEFAULT_MSIEVE_PATH` 和 `CURL_PATH`等。
3. **无限循环**：脚本会持续运行，直到手动按 `Ctrl+C` 中断。
4. **无超时控制**：如果 MSIEVE 分解大数耗时过长，脚本会一直等待。
5. **提交到公共数据库**：FactorDB 是公开数据库，提交前请确认符合其使用规则。
6. **因子解析有限**：脚本只解析 `factor:` 和 `pXX =` 格式，并仅校验整除性，不校验素性。
7. **日志会持续增长**：长期运行请注意清理 `log.txt`。
8. **线程数固定**：`MSIEVE_THREADS` 默认固定为 `5`，暂不支持命令行修改。
9. **FactorDB 预查询需要网络**：若网络异常，查询会失败并继续尝试分解。
10. **部分生成器可能产生偶数**：例如 `sophie`、`prefix` 等，程序会日志提示，`msieve` 会先提取因子 2。

## 版本历史

### v1.0

- 新增 9 种数字生成器：`random`、`repunit`、`mersenne`、`fermat`、`cunningham`、`factorial`、`primorial`、`sophie`、`prefix`。
- 新增 FactorDB API 预查询，已完全分解的数自动跳过。
- 因子上报改为从大到小排序；若 FactorDB 返回 `Already fully factored`，提前停止上报。
- 命令行新增 `--type`、`--base`、`--sign`、`--prefix`、`--list-types`、`--help`。
- 引入生成器注册表与统一生成入口，代码结构更清晰。
- 保持原有位置参数和命名参数用法兼容。
