# linkedin_video — the animated post asset

Renders `linkedin_sase_waf_ddos.mp4`: 7 square (1080x1080) frames telling the
WAF -> DDoS -> SASE story from `linkedin_ddos_post.md`, joined with **slow crossfades**
so each frame is readable in an autoplaying, muted, silent LinkedIn feed.

## Run

```
cd "C:\Python SW\Linkedin Scraper"
python linkedin_video/make_video.py
```

Options: `--hold 6` (seconds a frame is fully visible, default 4.5) · `--fade 1.5`
(dissolve seconds, default 1.2) · `--gif` (also emit a GIF — bigger and worse than the
MP4; LinkedIn plays MP4 natively, so only use it where a GIF is required) · `--out PATH`.

Requires **ffmpeg** on PATH (`winget install Gyan.FFmpeg`) and Pillow.

## Files
- `frames.py`  — draws the 7 PNGs (Colt palette: navy/teal/gold/red, `> colt` wordmark,
  `» » » » »` footer). Run alone with `--out DIR` to inspect frames without encoding.
- `make_video.py` — renders the frames, then chains them with ffmpeg `xfade`.
- `frames/` — generated PNGs (gitignored).

## Things that are easy to get wrong
- **Each xfade input must be `hold + fade` long**, not `hold`. If a clip ends exactly when
  its dissolve starts, ffmpeg silently truncates the tail and the frame flashes.
- **Frames are measured and vertically centred** (`slide()` draws onto an RGBA layer, takes
  `getbbox()`, then re-pastes). Top-aligning left ~350px of dead space and looked broken.
- Big display numbers need real descender room (`+196`, not `+168`) or the `p` in "Tbps"
  collides with the line beneath.
- Fonts resolve DejaVu (Linux) *or* Arial/Consolas (Windows) and fall back rather than
  crashing — the same script has to run in CI and on the laptop.

## Editing the story
Slide copy lives at the bottom of `frames.py` as `slide(...)` calls. `B`/`Bm`/`Bt`/`Bg` set
the line colour (ink / muted / teal / gold). Change copy, re-run `make_video.py`.
