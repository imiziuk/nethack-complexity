# Media: NetHack boulders behave like Push-1F

Made 2026-10-29 from the real NetHack 5.0.0 game (headless tty build of 16ff591 in WSL, `~/nh-witness/install`).
Each level was loaded with `#wizloadlua`, then every move was typed into the terminal like a player would.
After each key the tty output went through a VT100 emulator (pyte); each map square is drawn from the character the
game printed (symset DECgraphics, `boulder:0`) using NetHack's own 16x16 tiles (`win/share/{other,objects,monsters}.txt`).
The message line and status line in each frame are the game's own text. Added on top: the labels g / a / b,
"sealed pit", the captions and the title cards.

**Caveat:** the video shows the boulder mechanics the proof relies on. The complexity result itself is the written
proof in `proofs/hu-off.md` (plus the published Push-1F theorem, Ani et al., FUN 2022), not this video.

## Files
| File | Shows |
|---|---|
| `nethack_push1f_demo.mp4` | the full demo, 1280x720, about 90 s: title card, scenes 1-5, closing caveat card |
| `nethack_push1f_demo.gif` | same timeline at 640x360 (fallback) |
| `screenshots/00_title.png` | title card |
| `screenshots/a1_push_00.png` | scene 1 start: hero, boulder, corridor |
| `screenshots/a1_push_05.png` | push into the wall refused ("You try to move the boulder, but in vain.") |
| `screenshots/a1_push_06.png` | `m` + east: heavy hero still cannot enter the boulder square ("There is a boulder in your way.") |
| `screenshots/a2_diag_00.png` | scene 2 start: boulder diagonal to the hero |
| `screenshots/a2_diag_01.png` | diagonal push refused ("The boulder won't roll diagonally on this floor.") |
| `screenshots/a2_diag_03.png` | the same boulder pushed orthogonally works |
| `screenshots/a3_squeeze_00.png` | scene 3 start: two boulders on the diagonal's corners |
| `screenshots/a3_squeeze_01.png` | diagonal step between them refused ("You cannot pass that way.") |
| `screenshots/a3_squeeze_03.png` | after one orthogonal push the way is open |
| `screenshots/b_wrong_00.png` | puzzle start (goal g) |
| `screenshots/b_wrong_04.png` | wrong order: the boulder in front of g is pushed onto g |
| `screenshots/b_wrong_05.png` | it cannot be pushed off (wall behind) |
| `screenshots/b_wrong_10.png` | after clearing the other boulder: still stuck, g unreachable for good |
| `screenshots/b_right_00.png` | same puzzle, fresh start |
| `screenshots/b_right_07.png` | right order (upper boulder away, lower boulder into the pocket): hero on g |
| `screenshots/c_oneway_00.png` | self-closing one-way door, hero at a |
| `screenshots/c_oneway_06.png` | hero reached b; the door boulder is back in the doorway behind him |
| `screenshots/c_oneway_09.png` | trying to return: push refused, no way back to a |
| `build/frames.json` | raw capture: every 24x80 screen, key and label (the evidence the images are drawn from) |

## Levels (tools/visual/levels/)
Each level is an L_OFF-style instance as in `proofs/hu-off.md` B.2: `mongen=false`, `hunger=false`, flags
`noflip, sokoban, noteleport, hardfloor, solidify`, solidfill stone, explicit map at (1,0), boulders, one-cell
hero start region, hero inventory = one cursed loadstone, `pettype:none`, human female lawful Valkyrie.
Differences from the bare reduction, all for the demo only:
- `premapped` flag and a lit `des.region` over the map, so the whole board is visible (boulders block sight).
- The DL1 branch up-stair is forced into a sealed 1-cell pocket with `des.levregion{type="branch"}` (review-3), and
  `capture.py` checks on screen that the hero starts on the intended square (it reloads the level otherwise; no
  retry was needed). The pocket lies outside the drawn area.
- Scenes 4 and 5 include the sealed sentinel pit of the reduction (shown, labelled, unreachable).

The puzzle (scene 4) and the door (scene 5) were found and checked with `tools/visual/push1f.py` (BFS Push-1F solver):
the puzzle is solvable only if the upper boulder is moved before the lower one, and pushing the lower boulder east
first makes g unreachable; for the door, a reaches b, b cannot reach a, and after crossing there is no way back.
The door is our own small example, in the spirit of the paper's self-closing doors, not a gadget copied from it.

## Rebuild
```
wsl -d Ubuntu -- bash tools/visual/run_capture.sh   # plays the game, writes media/build/frames.json
wsl -d Ubuntu -- bash tools/visual/run_render.sh    # screenshots, MP4, GIF
```
Needs the venv `~/nh-witness/venv` (pexpect, pyte, Pillow, imageio-ffmpeg) and Windows fonts (Segoe UI, Consolas).
