# Skills

用于在不同电脑、不同智能体之间复用的技能。

## 三维技术微课制作

`technical-course-video` 可以根据讲稿、参考图和旁白制作工程原理微课，也可以按时间段修订已有成片。它指导智能体拆分镜、制作关键动作样片、按旁白安排动画和标注、对齐中文字幕、加入章节标题，并输出经过帧数、时长和音轨检查的 MP4。

随包合片脚本使用 **Python 3.9+ 和 FFmpeg**。新制三维镜头用 **Blender**。静态参考图可选 **ComfyUI**，新配音可选 **IndexTTS2**，字幕时间定位可选 **Whisper**。已有视频和录音可以直接用于后期处理。具体依赖及示例见 [技能说明](technical-course-video/README.md) 和 [SKILL.md](technical-course-video/SKILL.md)。

## 给智能体的安装提示词

把下面整段复制给你要使用的智能体：

```text
请从 https://github.com/hitman9099/skills/tree/main/technical-course-video 安装 technical-course-video 技能。
如果支持 Codex 的 $skill-installer，就用它安装这个 GitHub 子目录。
否则，下载 technical-course-video 的完整目录，将它放到当前智能体会扫描的技能目录中，并保留 SKILL.md、agents、assets、references 和 scripts 的相对结构。
确认安装目录里的 SKILL.md 可以读取，说明实际安装路径和调用方式。若这个智能体没有技能安装功能，请直接加载该目录的 SKILL.md 和任务所需的参考文件。
```

在 Codex 中，安装后在新对话输入 `$technical-course-video`，并提供讲稿、参考素材或需要修订的成片。
