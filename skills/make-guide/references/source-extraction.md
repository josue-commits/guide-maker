# Source Material Extraction

## Method A: YouTube Video

Extract the transcript with yt-dlp (`tools.ytdlp_path` in the config, or the one on PATH):

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download --sub-format srt -o "{WORK_DIR}/yt/%(title)s" <URL>
```

If auto-subs are unavailable, try manual subs:

```bash
yt-dlp --write-sub --sub-lang en --skip-download --sub-format srt -o "{WORK_DIR}/yt/%(title)s" <URL>
```

Read the `.srt` (or `.vtt`) file that gets downloaded. Strip timing data and repeated lines, then clean the raw transcript before classifying. `tests/fixtures/sample-transcript.vtt` shows the shape.

## Method B: Pasted Transcript

Accept the transcript directly. Read it in full before doing anything else.

## Method C: Topic Research

When the user provides a topic (or Phase 0 proposed one):
1. Read the scan files under `{WORK_DIR}/scan/` if they exist; they carry every resource the three sources found for the topic
2. Web search for 2-3 strong sources beyond them (official docs, the repo, an institutional talk)
3. Synthesize into an original guide, not a summary of sources

Whatever the method, every claim is verified against a primary source before it reaches the outline (`references/research/topic-research.md`, section 7).
