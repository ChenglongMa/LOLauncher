<div style="text-align:center;">
    <img src="./docs/icon.svg" alt="LOLauncher logo" width="400px">
</div>

![macOS Version](https://img.shields.io/badge/WinOS_Version-10%2B-green?logo=windows)
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/ChenglongMa/LOLauncher?include_prereleases)](https://github.com/ChenglongMa/LOLauncher/releases/latest)
[![GitHub License](https://img.shields.io/github/license/ChenglongMa/LOLauncher)](https://github.com/ChenglongMa/LOLauncher/blob/main/LICENSE)
[![youtube](https://img.shields.io/badge/参考教程-FF0000?logo=youtube)](https://youtu.be/gNkLY6EAsaU?si=Q-WdWD7Jt7Oyik_w)
[![Downloads](https://img.shields.io/github/downloads/ChenglongMa/LOLauncher/total)](https://github.com/ChenglongMa/LOLauncher/releases/latest)

# 英雄联盟，启动！

* 该程序用于修改英雄联盟默认的语言为**中文**并启动游戏。
* 当然你也可以参考 [下方手动配置章节](#手动配置) 将其改为其他语言。
* 该程序参考 [![youtube](https://img.shields.io/badge/大神制作的视频教程-FF0000?logo=youtube)](https://youtu.be/gNkLY6EAsaU?si=Q-WdWD7Jt7Oyik_w) 编写。
* 该程序**目前**在 Windows 系统下测试通过。MacOS 版本正在开发中。
* 该程序目前适用于英雄联盟的14.9版本，特别是[Riot Vanguard](https://www.leagueoflegends.com/en-us/news/game-updates/patch-14-9-notes/#patch-vanguard)发布后，以前的修改语言的方法已经失效。

## 安装并运行

1. 前往 [Release 页面](https://github.com/ChenglongMa/LOLauncher/releases/latest) 下载最新版本的 [LOLauncher.zip](https://github.com/ChenglongMa/LOLauncher/releases/latest/download/LOLauncher.zip)。
2. 解压缩 `LOLauncher.zip` 到任意目录。
3. 运行 `LOLauncher.exe`。

该程序会自动检测英雄联盟的相关目录修改配置并启动游戏。

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
- **注意：路径中的 `\` 需要转义为 `\\`，或者使用 `/` （请参考以上示例）。**
