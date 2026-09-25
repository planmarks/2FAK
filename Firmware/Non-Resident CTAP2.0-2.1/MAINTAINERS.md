## Firmware release process
1. Tag the commit to be released with the next firmware version
1. Build the firmware using Docker
2. Sign the binary firmware
3. Upload signed binary to the Github releases
4. Bump ./STABLE_RELEASE file with the latest version
5. Run update script on the update server (if needed)

## Signing firmware

To sign the firmware it suffices to call pynitrokey like this:

```text
nitropy fido2 util sign VERIFYING_KEY APP_HEX OUTPUT_JSON
```

### 128kB variant

During the firmware signing the smaller MCU version has to be indicated during signing with the `--pages` switch, like:

```text
nitropy fido2 util sign --pages 64 ....
```

The rest of the invocation is the same, e.g.:
```text
nitropy fido2 util sign --pages 64 VERIFYING_KEY APP_HEX OUTPUT_JSON
```