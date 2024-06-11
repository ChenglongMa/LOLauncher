<p align="center">
    <img src="./docs/icon.svg" alt="LOLauncher logo" width="400px">
</p>

<div align="center">

![macOS Version](https://img.shields.io/badge/WinOS_Version-10%2B-green?logo=windows)
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/ChenglongMa/LOLauncher?include_prereleases)](https://github.com/ChenglongMa/LOLauncher/releases/latest)
[![GitHub License](https://img.shields.io/github/license/ChenglongMa/LOLauncher)](https://github.com/ChenglongMa/LOLauncher/blob/main/LICENSE)
[![youtube](https://img.shields.io/badge/参考教程-YouTube-FF0000?logo=youtube)](https://youtu.be/gNkLY6EAsaU?si=Q-WdWD7Jt7Oyik_w)
[![Bilibili](https://img.shields.io/badge/参考教程-Bilibili-1E88E5?logo=bilibili)](https://www.bilibili.com/video/BV1Zs421P7EB)
[![Downloads](https://img.shields.io/github/downloads/ChenglongMa/LOLauncher/total)](https://github.com/ChenglongMa/LOLauncher/releases/latest)

</div>

# 英雄联盟，启动！

* 该程序用于修改英雄联盟的文本语言为**简体中文**，语音为**国服语音**，并启动游戏。
* 当然你也可以参考 [下方手动配置章节](#手动配置) 将其改为其他语言。
* 该程序参考视频教程 [![youtube](https://img.shields.io/badge/YouTube_版本-FF0000?logo=youtube)](https://youtu.be/gNkLY6EAsaU?si=Q-WdWD7Jt7Oyik_w) 或 [![Bilibili](https://img.shields.io/badge/Bilibili_版本-white?logo=bilibili)](https://www.bilibili.com/video/BV1Zs421P7EB) 编写。
* 该程序**目前**在 Windows 系统下测试通过。MacOS 版本正在开发中。
* 该程序目前适用于英雄联盟的14.9版本，特别是 [Riot Vanguard](https://www.leagueoflegends.com/en-us/news/game-updates/patch-14-9-notes/#patch-vanguard) 发布后，以前的修改语言的方法已经失效。

_如何您喜欢该项目，欢迎点一个⭐！_

_如果您有任何问题，请在 [Discussions](https://github.com/ChenglongMa/LOLauncher/discussions) 或 [Issues](https://github.com/ChenglongMa/LOLauncher/issues) 中讨论，也可以给我发邮件 [chenglong.m_at_outlook.com](mailto:chenglong.m@outlook.com)。_

_谢谢关注！_

## 安装并运行

1. 前往 [Release 页面](https://github.com/ChenglongMa/LOLauncher/releases/latest) 下载最新版本的 [LOLauncher.zip](https://github.com/ChenglongMa/LOLauncher/releases/latest/download/LOLauncher.zip)。
2. 解压缩 `LOLauncher.zip` 到任意目录。
3. 运行 `LOLauncher.exe`。

该程序会自动检测英雄联盟的相关目录修改配置并启动游戏。

### 注意 
1. 该程序需要**管理员权限**运行。这是因为需要将游戏的配置文件设置为只读，以防止游戏更新后恢复默认语言。
2. 游戏启动成功后**不需要**再次运行该程序，可按照您的习惯启动游戏。若之后游戏更新导致语言恢复，可重新运行该程序。
3. 本程序会**自动检查更新**，如果有新版本会提示您下载。我会根据游戏的更新情况及时更新程序。

> [!TIP]
> 
> 如果您想要完整的翻译, 请在打开游戏后先**关闭一次**, 然后会弹出以下界面:
> 
> ![更新按钮](docs/update-prompt.png)
> 
> 请**毫不犹豫**地点击 `更新` 按钮!
> 
> 之后进入游戏就会看到完整的翻译了 🍻
> 
> (比较遗憾的是, 该操作目前无法通过程序自动完成, 但是我会尽快想办法更新程序以支持该功能)

*如果你想手动配置相关文件路径，可以参考以下文档：*

## 手动配置

首次运行程序后，会在`C:\Users\<你的用户名>\.lolauncher`下生成 `config.json` 文件，你可以在该文件中手动配置相关路径。

```json
{
  "SettingFile": "C:\\ProgramData\\Riot Games\\Metadata\\league_of_legends.live\\league_of_legends.live.product_settings.yaml",
  "GameClient": "C:/Games/Riot Games/Riot Client/RiotClientServices.exe",
  "Locale": "zh_CN"
}
```

- `SettingFile`：英雄联盟的 `league_of_legends.live.product_settings.yaml` 配置文件路径。
- `GameClient`：Riot 客户端<img src="./docs/lol_client.ico" alt="Riot 客户端 icon" width="40px">的 `RiotClientServices.exe` 文件路径。
- `Locale`：游戏语言，例如 `zh_CN` 为中文，`en_US` 为英文。
- **注意：路径中的 `\` 需要替换为 `\\`，或者使用 `/` （请参考以上示例）。**

## 常见问题

### 1. 程序失效，游戏语言未修改成功。

**解决方案**：您可以参考视频教程 [![youtube](https://img.shields.io/badge/YouTube_版本-FF0000?logo=youtube)](https://youtu.be/gNkLY6EAsaU?si=Q-WdWD7Jt7Oyik_w) 或 [![Bilibili](https://img.shields.io/badge/Bilibili_版本-white?logo=bilibili)](https://www.bilibili.com/video/BV1Zs421P7EB) 手动修改游戏语言。

如果依然有问题，请在 [Discussions](https://github.com/ChenglongMa/LOLauncher/discussions) 或 [Issues](https://github.com/ChenglongMa/LOLauncher/issues) 中讨论，也可以给我发邮件 [chenglong.m_at_outlook.com](mailto:chenglong.m@outlook.com)。

### 2. 运行程序时弹出 `Windows Defender 防病毒` 警告。

**解决方案**：这是由于该程序没有签名导致的。该程序代码完全开源，只是数字证书太贵了，我无力购买🥺。

如果您信任该程序，请点击 `More info`（`更多信息`），然后点击 `Run anyway`（`仍要运行`）。

该操作只需一次，后续不会再弹出警告。

<img alt="Windows Defender" src="./docs/win-warning1.png" width="80%"/>
<img alt="Windows Run" src="./docs/win-warning2.png" width="80%"/>
