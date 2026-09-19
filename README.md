# autosieve

> 基于 Windows、CURL 和 MSIEVE 的 FactorDB 自动提交系统

`autosieve` 是一个 Python 3 自动化脚本，用于循环生成指定长度的随机奇数，调用 [MSIEVE](https://github.com/radii/msieve) 进行整数分解，提取有效因子，并通过 `curl` 将因子自动提交到 [FactorDB](https://factordb.com/)。

---

## 功能特性

- 自动生成指定十进制位数的随机奇数
- 调用 `msieve` 进行整数分解
- 从 `msieve` 标准输出和 `msieve.log` 中解析因子
- 校验因子能否整除原数，过滤无效结果
- 通过 `curl` 将因子提交到 FactorDB
- 支持命令行参数覆盖默认配置
- 自动记录运行日志到 `log.txt`
- 支持 `Ctrl+C` 安全退出

---

## 工作流程

1. 生成一个指定长度的随机奇数。
2. 执行 `msieve -v -t 5 <number>` 进行分解。
3. 读取 `msieve` 输出和日志，解析 `factor:`、`pXX =` 等格式的因子。
4. 校验每个因子是否能整除原数。
5. 对每个有效因子，使用 `curl` 向 FactorDB 提交：
   ```text
   number=<原数>&factor=<因子>
   ```
6. 休眠 1 秒，继续下一轮。

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

```python
DEFAULT_DIGITS = 80
DEFAULT_FDBUSER = ""
DEFAULT_MSIEVE_PATH = r"D:\MSIEVE\msieve.exe"
MSIEVE_THREADS = 5
CURL_PATH = "curl.exe"
FACTORDB_URL = "https://factordb.com/reportfactor.php"
```

配置说明：

| 配置项 | 说明 | 默认值 |
|---|---|---|
| `DEFAULT_DIGITS` | 默认生成奇数的十进制位数 | `80` |
| `DEFAULT_FDBUSER` | FactorDB 用户名 | `""` |
| `DEFAULT_MSIEVE_PATH` | `msieve.exe` 路径 | `D:\MSIEVE\msieve.exe` |
| `MSIEVE_THREADS` | MSIEVE 使用的线程数 | `5` |
| `CURL_PATH` | curl 可执行文件路径 | `curl.exe` |
| `FACTORDB_URL` | FactorDB 提交地址 | `https://factordb.com/reportfactor.php` |

---

## 使用方法

### 位置参数

```bash
python autosieve.py [位数] [fdbuser] [msieve路径]
```

示例：

```bash
python autosieve.py
```

使用默认配置：80 位、空 fdbuser、`D:\MSIEVE\msieve.exe`。

```bash
python autosieve.py 100
```

生成 100 位随机奇数。

```bash
python autosieve.py 100 myuser
```

生成 100 位随机奇数，并以 `myuser` 身份提交到 FactorDB。

```bash
python autosieve.py 100 myuser D:\MSIEVE\msieve.exe
```

指定完整参数。

### 命名参数

```bash
python autosieve.py --digits 100 --fdbuser myuser --msieve D:\MSIEVE\msieve.exe
```

也支持等号形式：

```bash
python autosieve.py --digits=100 --fdbuser=myuser --msieve=D:\MSIEVE\msieve.exe
```

### 参数说明

| 参数 | 说明 |
|---|---|
| `位数` / `--digits` | 生成奇数的十进制位数，默认 `80` |
| `fdbuser` / `--fdbuser` | FactorDB 用户名，用于提交时携带 cookie |
| `msieve路径` / `--msieve` | `msieve.exe` 的完整路径 |

位置参数和命名参数可以混用。命名参数先解析，位置参数后覆盖。

---

## 日志

脚本会在同目录下生成 `log.txt`，以追加方式记录运行信息，包括：

- 启动配置
- 生成的随机数
- MSIEVE 执行命令
- MSIEVE 原始输出
- 解析到的因子
- 因子校验结果
- FactorDB 提交结果
- 异常信息

日志同时输出到控制台。

---

## 注意事项

1. **依赖外部程序**：必须正确安装 `msieve` 和 `curl`。
2. **默认路径为 Windows 风格**：Linux/macOS 下需要修改 `DEFAULT_MSIEVE_PATH` 和 `CURL_PATH`。
3. **无限循环**：脚本会持续运行，直到手动按 `Ctrl+C` 中断。
4. **无超时控制**：如果 MSIEVE 分解大数耗时过长，脚本会一直等待。
5. **提交到公共数据库**：FactorDB 是公开数据库，提交前请确认符合其使用规则。
6. **因子解析有限**：脚本只解析 `factor:` 和 `pXX =` 格式，并仅校验整除性，不校验素性。
7. **日志会持续增长**：长期运行请注意清理 `log.txt`。
8. **线程数固定**：`MSIEVE_THREADS` 默认固定为 `5`，暂不支持命令行修改。
