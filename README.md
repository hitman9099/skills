# Skills

用于在不同电脑、不同智能体之间复用的技能。

| 技能 | 用途 | 入口 |
| --- | --- | --- |
| `technical-course-video` | 制作或修订技术微课与三维教学视频，按旁白组织动作、字幕和章节，再合片核验。 | [安装与使用](technical-course-video/README.md) · [SKILL.md](technical-course-video/SKILL.md) |

## 给智能体的安装提示词

把下面整段复制给你要使用的智能体：

```text
请从 https://github.com/hitman9099/skills/tree/main/technical-course-video 安装 technical-course-video 技能。
如果支持 Codex 的 $skill-installer，就用它安装这个 GitHub 子目录。
否则，下载 technical-course-video 的完整目录，将它放到当前智能体会扫描的技能目录中，并保留 SKILL.md、agents、assets、references 和 scripts 的相对结构。
确认安装目录里的 SKILL.md 可以读取，说明实际安装路径和调用方式。若这个智能体没有技能安装功能，请直接加载该目录的 SKILL.md 和任务所需的参考文件。
```

在 Codex 中，安装后在新对话输入 `$technical-course-video`，并提供讲稿、参考素材或需要修订的成片。
