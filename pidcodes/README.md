# pid.codes PID allocation (0x1209 / 0x2FA2)

This folder holds the file to submit to **pid.codes** to reserve PID `0x2FA2` under
the shared open-source Vendor ID `0x1209`, so the 2FAK VID/PID is officially recorded
and does not collide with another open-source project.

## How to submit (do this once)

1. Open <https://pid.codes/1209/> and confirm `2FA2` is still **unallocated**. If it is
   taken, pick another free 4-hex value (avoid `0001`-`000F`, reserved for testing),
   update `USBD_PID` in each firmware's `targets/stm32l432/src/app-common.h`, rebuild,
   and rename `1209/2FA2.md` accordingly.
2. Fork <https://github.com/pidcodes/pidcodes.github.com>.
3. Copy `1209/2FA2.md` from this folder into the fork at the same path (`1209/2FA2.md`).
4. Commit and open a Pull Request. pid.codes maintainers review and merge it; the merge
   is the allocation. It is free.

## Notes

- The `name` in the frontmatter is what appears on the public pid.codes page.
- Update the `Project:` URL in `1209/2FA2.md` to the final public repository URL before
  submitting.
- Requirement: the product is real and open-source, which this repository demonstrates.
