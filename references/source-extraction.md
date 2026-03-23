# Source Material Extraction

## Method A: YouTube Video

Extract the transcript using yt-dlp:

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download -o "/tmp/guides/%(title)s" <URL>
```

If auto-subs are unavailable, try manual subs:

```bash
yt-dlp --write-sub --sub-lang en --skip-download -o "/tmp/guides/%(title)s" <URL>
```

Read the `.vtt` or `.srt` file that gets downloaded. Strip timing data and clean up the raw transcript before classifying.

## Method B: Pasted Transcript

Accept the transcript directly. Read it in full before doing anything else.

## Method C: Topic Research

When the user provides a topic (or the agent proposes one):
1. Use `WebSearch` to research the topic thoroughly
2. Find 2-3 strong sources (official docs, reputable tutorials, data)
3. Synthesize into an original guide, not a summary of sources
