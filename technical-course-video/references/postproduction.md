# 旁白、合片和核验

- 已有正确录音就直接用。只有短参考音时，用授权的音色参考生成新台词。先生成一段检查音色、专业词和语速。本地 IndexTTS2 是用过的选项，新环境可用合适的工具或真人录音。
- 用实际发音时间对齐字幕。可用本地 ASR 词级时间定位，以确认过的中文原稿显示，复听术语、声调和断句。拼音匹配只支持发音完整性判断，同音、声调和静音转写异常要复听。替换一句时复用其他原音。
- 优先统一响度及峰值，用 48 kHz 单声道 PCM16 WAV 交接。短于镜长的旁白可补静音。过长先改镜长或小幅调整语速，再对齐字幕。用整片累计时间换算采样边界，避免逐镜舍入积累漂移。

## 随包脚本

运行主机需要 Python 3.9+ 和带 `libx264`、`libass` 的 FFmpeg。脚本只使用 Python 标准库。用系统识别的 Python 启动命令，如 Windows 的 `py -3` 或 macOS/Linux 的 `python3`。FFmpeg 在 PATH 时可省略 `--ffmpeg`，便携版传入可执行文件的完整路径。

```text
python3 /path/to/technical-course-video/scripts/course_video.py --ffmpeg /path/to/ffmpeg doctor
python3 /path/to/technical-course-video/scripts/course_video.py --ffmpeg /path/to/ffmpeg build /path/to/project/course.json /path/to/project/final.mp4
```

复制 [course.json](../assets/course.json) 并填写。素材路径相对于清单，也可用绝对路径。设置 `canvas`、`fps`（如 `30` 或 `30000/1001`）、`font`（本机中文字体族名）、可选 `font_dir`（额外字体目录）、`chapter_corner`（`left` 或 `right`）。每镜含 `id`、`frames`、`video`、`chapter`、`narration`、`captions`：

- `video` 用已渲好的视频。静图加 `still: true`。默认从第一帧开始，`start_frame` 是帧率统一后的源画面入点。源画面不足会报错，源更长会按 `frames` 截取。比例不同时等比缩放、留边。转帧不使用光流。
- `narration` 指向该镜 48 kHz 单声道 PCM16 WAV，省略可做无旁白镜头。音频短了在尾部补静音，长了报错。`captions` 每项填本镜内的秒数 `start`、`end` 和 `text`。字幕不重叠、不越镜。
- 同一章重复填写相同 `chapter`，标题在整镜持续显示。源画面已有字幕或标题时省略对应字段。公式、对象标注、翼面高亮、流场动画在交给脚本前完成。
- 脚本自动检查整片可解码、尺寸、帧数、连续时间戳和 AAC 解码样本量。还需看成品抽帧、听关键句，确认字体有字、标题不遮挡且音画对应。

## 其他剪辑管线

先统一尺寸、色彩、帧率和时基。烧字幕前试一镜中文和公式。拼接已编码片段时用仅视频的中间片段，WAV 按顺序拼为一条音轨后一次编码 AAC。时间轴不变时可直接复制完整原音轨。通过实际解码核对首尾帧和时间戳；容器的平均帧率数值不足以排除最后一帧丢失。

交付前看章首章尾、字幕进出、受力和流向及用户指出的时间点。成片链接附实际规格。有升采样、转帧、教学近似或指定音色的重新合成时，清楚说明范围。
