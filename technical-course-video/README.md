# 三维技术微课制作 · technical-course-video

适合根据讲稿制作技术微课、工程原理讲解视频，或修订现有成片的动作、旁白、标注、字幕和章节标题。技能包含分镜模板、Blender 动画检查方法，以及 FFmpeg 合片与核验脚本。

## 安装

- **Codex**：在对话中输入 `$skill-installer https://github.com/hitman9099/skills/tree/main/technical-course-video`。安装后在新对话中用 `$technical-course-video` 调用。
- **手动安装**：克隆 [本仓库](https://github.com/hitman9099/skills) 或下载其 ZIP，把完整的 `technical-course-video` 文件夹复制到本机智能体扫描的技能目录。Codex 可使用个人目录 `~/.agents/skills/` 或项目的 `.agents/skills/`。使用其他智能体时，按其安装约定保留目录内的相对路径。
- **临时加载**：让智能体先读 [SKILL.md](SKILL.md)，再按任务读取其中链接的参考文件、模板和脚本。

## 调用示例

```text
用 $technical-course-video，根据我提供的讲稿和参考图制作工程原理微课。
先做关键动作样片，再制作整片。让画面变化跟随旁白，交付 2560×1440、30 fps 的 MP4。
```

也可直接给出已有成片和修订时间段，例如“让 3:42–4:01 的画面跟随解说变化，保留现有章节、旁白和字幕”。

## 换电脑时需要的素材和工具

随包的 [课程清单](assets/course.json) 用相对路径连接镜头、旁白、字幕和章节。[合片脚本及用法](references/postproduction.md) 需要 Python 3.9+ 与带 `libx264`、`libass` 的 FFmpeg。中文排版需要本机有合适字体。需要新制三维画面时准备 Blender；需要重新配音时准备录音或相应的语音工具。

继续同一个项目时，随技能一起迁移分镜、源模型、旁白、字幕、参考素材和当前成片。技能可以为新项目从头建立制作流程。
