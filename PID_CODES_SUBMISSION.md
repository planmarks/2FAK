# pid.codes submission (VID 0x1209 / PID 0x2FA2)

Reserves PID `0x2FA2` under the community open-source VID `0x1209` for 2FAK, per
<https://pid.codes/howto/>. The two files to submit mirror the pid.codes repo layout and
live in this repository:

- `org/muru.global/index.md` - the organisation page
- `1209/2FA2/index.md` - the PID page (`owner` must equal the org directory name)

## Steps

1. Confirm `2FA2` is still free at <https://pid.codes/1209/>. If it is taken, choose another
   free hexadecimal value `>= 0x2000` (`0xxx` and `1xxx` are reserved), update `USBD_PID` in
   BOTH firmwares' `targets/stm32l432/src/app-common.h` to match, rebuild, and rename the
   `1209/<PID>/` directory accordingly.
2. Fork <https://github.com/pidcodes/pidcodes.github.com>.
3. Copy `org/muru.global/` and `1209/2FA2/` into the fork at the same paths.
4. Commit and open a Pull Request; the maintainers' merge is the allocation. It is free.

## Notes

- PID frontmatter fields (howto): `layout: pid`, `title`, `owner` (= the org directory
  name), `license` (an SPDX id), `site` (optional), `source` (public repo URL). The `title`
  is automatically prefixed with the org name, so it renders as
  "muru.global 2FAK Security Key" - do not add a separate `name` field.
- Set `site`/`source` to the final public repository URL before submitting.
- The product must be real and open-source, which this repository demonstrates.
